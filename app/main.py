import json
import os
from typing import Annotated

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from .auth import autenticar_usuario, exigir_admin, exigir_login, hash_senha
from .db import (
    criar_versao_anteprojeto,
    get_conn,
    init_db,
    normalize_chave,
    obter_caminho_equipamento,
    obter_opcoes_disponiveis,
    registrar_historico_anteprojeto,
    touch_anteprojeto,
)
from .pdf import gerar_pdf_anteprojeto


app = FastAPI(title="Anteprojetos de Armazenagem Agricola")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "dev-secret-change-me"),
)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

STATUS_OPCOES = [
    "Rascunho",
    "Enviado para engenharia",
    "Retornado",
    "Revisado",
    "Aprovado",
    "Finalizado",
    "Cancelado",
]
STATUS_GERA_VERSAO = {
    "Enviado para engenharia": "Envio para engenharia",
    "Retornado": "Retorno da engenharia",
    "Aprovado": "Aprovacao",
    "Finalizado": "Aprovacao/finalizacao",
    "Cancelado": "Cancelamento",
}
TIPO_OBRA_OPCOES = ["Obra nova", "Reforma"]
TIPO_DEFINICAO_OPCOES = ["Ja definido", "Parcialmente definido", "Engenharia dimensionar"]
SITUACAO_REFORMA_OPCOES = ["Novo", "Existente", "Substituir", "Adequar", "Remover"]
TIPOS_CAMPO_EQUIPAMENTO = ["text", "number", "select", "checkbox", "textarea", "info"]
TIPOS_ATRIBUTO_EQUIPAMENTO = ["texto", "numero", "inteiro", "booleano", "lista", "json"]
TIPOS_OPCAO_EQUIPAMENTO = ["booleano", "selecao", "texto", "numero"]


@app.on_event("startup")
def startup():
    init_db()


def parse_json_row(row, column="schema_json"):
    data = dict(row)
    data["schema"] = json.loads(data[column])
    return data


def get_atributos_equipamento(conn, equipamento_id, somente_resumo=False):
    filtro = "AND visivel_resumo = 1" if somente_resumo else ""
    return conn.execute(
        f"""
        SELECT * FROM equipamentos_atributos
        WHERE equipamento_id = ? {filtro}
        ORDER BY ordem, nome, id
        """,
        (equipamento_id,),
    ).fetchall()


def formatar_atributo_resumo(atributo):
    valor = atributo["valor"]
    if valor in (None, ""):
        valor = "-"
    elif atributo["tipo"] == "booleano":
        valor = "Sim" if str(valor).lower() in ("1", "true", "sim", "yes") else "Nao"
    unidade = atributo["unidade"] or ""
    return f"{atributo['nome']}: {valor}{(' ' + unidade) if unidade else ''}"


def montar_arvore_equipamentos(equipamentos):
    por_id = {}
    raiz = []

    for equipamento in equipamentos:
        item = dict(equipamento)
        item["filhos"] = []
        por_id[item["id"]] = item

    for item in por_id.values():
        parent_id = item.get("parent_id")
        if parent_id and parent_id in por_id:
            por_id[parent_id]["filhos"].append(item)
        else:
            raiz.append(item)

    def ordenar(nos):
        nos.sort(key=lambda item: item["id"])
        for no in nos:
            ordenar(no["filhos"])

    ordenar(raiz)
    return raiz


def obter_descendentes_equipamento(conn, equipamento_id):
    descendentes = set()
    pendentes = [equipamento_id]
    while pendentes:
        atual = pendentes.pop()
        filhos = conn.execute(
            "SELECT id FROM equipamentos_modelo WHERE parent_id = ?",
            (atual,),
        ).fetchall()
        for filho in filhos:
            if filho["id"] not in descendentes:
                descendentes.add(filho["id"])
                pendentes.append(filho["id"])
    return descendentes


def get_opcoes_pai_equipamento(conn, equipamento_id=None):
    bloqueados = {equipamento_id} if equipamento_id else set()
    if equipamento_id:
        bloqueados.update(obter_descendentes_equipamento(conn, equipamento_id))

    opcoes = []
    rows = conn.execute("SELECT id FROM equipamentos_modelo ORDER BY nome").fetchall()
    for row in rows:
        if row["id"] in bloqueados:
            continue
        opcoes.append({"id": row["id"], "caminho": obter_caminho_equipamento(conn, row["id"])})
    opcoes.sort(key=lambda item: item["caminho"].lower())
    return opcoes


def has_filhos_equipamento(conn, equipamento_id):
    return bool(
        conn.execute(
            "SELECT 1 FROM equipamentos_modelo WHERE parent_id = ? LIMIT 1",
            (equipamento_id,),
        ).fetchone()
    )


def obter_cadeia_equipamento(conn, equipamento_id):
    cadeia = []
    visitados = set()
    atual_id = equipamento_id

    while atual_id and atual_id not in visitados:
        visitados.add(atual_id)
        row = conn.execute(
            "SELECT id, parent_id, nome FROM equipamentos_modelo WHERE id = ?",
            (atual_id,),
        ).fetchone()
        if not row:
            break
        cadeia.append(dict(row))
        atual_id = row["parent_id"]

    return list(reversed(cadeia))


def get_anteprojeto_or_404(conn, anteprojeto_id):
    anteprojeto = conn.execute("SELECT * FROM anteprojetos WHERE id = ?", (anteprojeto_id,)).fetchone()
    if not anteprojeto:
        raise HTTPException(status_code=404, detail="Anteprojeto nao encontrado")
    return anteprojeto


def collect_campos(form, equipamento_schema):
    campos = {}
    for campo in equipamento_schema.get("campos", []):
        nome = campo["nome"]
        tipo = campo["tipo"]
        key = f"campo__{nome}"
        if tipo == "info":
            continue
        if tipo == "checkbox":
            campos[nome] = form.getlist(key)
        else:
            campos[nome] = (form.get(key) or "").strip()
    return campos


def parse_item(row):
    item = dict(row)
    item["campos"] = json.loads(item["campos_json"] or "{}")
    item["opcoes"] = []
    item["resumo_fluxo"] = ""
    item["resumo_transportador"] = ""
    item["resumo_maquina_limpeza"] = ""
    item["resumo_secador"] = ""
    item["resumo_silo_pulmao"] = ""
    return item


def equipamento_nome_exibicao(nome):
    if nome == "Item 1 - Fluxo":
        return "Fluxo"
    if nome == "Item 2 - Transportadores":
        return "Transportador"
    if nome == "Item 3 - Máquina de Limpeza Grain Cleaner EC":
        return "Máquina de Limpeza Grain Cleaner EC"
    if nome == "Item 4 - Secadores Process Dryer":
        return "Secador Process Dryer"
    if nome == "Item 5 - Silo Pulmão Elevado":
        return "Silo Pulmão Elevado"
    return nome


def resumo_fluxo(opcoes):
    dados = {opcao["opcao_chave"]: opcao for opcao in opcoes}
    tipo = dados.get("tipo_fluxo", {}).get("valor_rotulo") or "-"
    graos = dados.get("fluxo_graos", {}).get("valor_rotulo") or "-"
    impurezas_habilitado = dados.get("fluxo_impurezas_habilitado", {}).get("valor") == "sim"
    moega = dados.get("moega", {}).get("valor_rotulo") or "-"
    if impurezas_habilitado:
        impurezas_valor = dados.get("fluxo_impurezas", {}).get("valor_rotulo") or "-"
        impurezas = f"Sim - {impurezas_valor}"
    else:
        impurezas = "Não"
    return f"Fluxo | Tipo: {tipo} | Grãos: {graos} | Impurezas: {impurezas} | Moega: {moega}"


def resumo_transportador(campos):
    tipo = campos.get("tipo_rotulo") or "-"
    subtipo = campos.get("subtipo_rotulo") or ""
    equipamento = f"{tipo} {subtipo}".strip()
    sensores = []
    acessorios = []
    for item in campos.get("sensores_acessorios") or []:
        nome_resumo = item.get("resumo") or item.get("nome") or ""
        if not nome_resumo:
            continue
        if item.get("categoria") == "acessorio":
            acessorios.append(nome_resumo)
        else:
            sensores.append(nome_resumo)

    partes = [f"Transportador | {equipamento}"]
    if sensores:
        partes.append(f"Sensores: {', '.join(sensores)}")
    if acessorios:
        partes.append(f"Acessórios: {', '.join(acessorios)}")
    return " | ".join(partes)


def resumo_maquina_limpeza(campos):
    tipo = campos.get("tipo_limpeza_rotulo") or "-"
    modelo = campos.get("modelo_rotulo") or "-"
    return f"Máquina de Limpeza Grain Cleaner EC | {tipo} | {modelo}"


MAQUINA_LIMPEZA_TIPOS = {
    "pre_limpeza": "Pré-Limpeza",
    "pos_limpeza": "Pós-Limpeza",
}
MAQUINA_LIMPEZA_MODELOS = {
    "mle_45_60": "MLE 45 - 60 t/h",
    "mle_95_120": "MLE 95 - 120 t/h",
    "mle_145_180": "MLE 145 - 180 t/h",
    "mle_190_240": "MLE 190 - 240 t/h",
    "mle_45_47": "MLE 45 - 47 t/h",
    "mle_95_96": "MLE 95 - 96 t/h",
    "mle_145_144": "MLE 145 - 144 t/h",
    "mle_190_192": "MLE 190 - 192 t/h",
}


def collect_maquina_limpeza_campos(form):
    tipo = (form.get("maquina_limpeza_tipo") or "").strip()
    modelo = (form.get("maquina_limpeza_modelo") or "").strip()
    return {
        "tipo_limpeza": tipo,
        "tipo_limpeza_rotulo": MAQUINA_LIMPEZA_TIPOS.get(tipo, tipo),
        "modelo": modelo,
        "modelo_rotulo": MAQUINA_LIMPEZA_MODELOS.get(modelo, modelo),
    }


def resumo_secador(campos):
    modelo = campos.get("modelo_rotulo") or "-"
    fornalha = campos.get("fornalha") or "sem"
    alimentador = campos.get("alimentador") or "sem"
    partes = [f"Secador Process Dryer | {modelo}"]
    if fornalha == "com":
        combustivel = campos.get("combustivel_rotulo") or "-"
        partes.append(f"Fornalha Black Velox - {combustivel}")
    else:
        partes.append("Sem Fornalha")
    if alimentador == "com":
        volume = campos.get("alimentador_volume_rotulo") or "-"
        partes.append(f"Alimentador de Cavaco - {volume}")
    else:
        partes.append("Sem Alimentador")
    return " | ".join(partes)


SECADOR_MODELOS = {
    "scc_202_22": "SCC-202 - 22 t/h",
    "scc_302_33": "SCC-302 - 33 t/h",
    "scc_303_49": "SCC-303 - 49 t/h",
    "scc_304_66": "SCC-304 - 66 t/h",
    "scc_404_88": "SCC-404 - 88 t/h",
    "scc_504_110": "SCC-504 - 110 t/h",
    "scc_505_138": "SCC-505 - 138 t/h",
    "scc_605_165": "SCC-605 - 165 t/h",
    "scc_705_193": "SCC-705 - 193 t/h",
    "scc_707_238": "SCC-707 - 238 t/h",
    "scc_707_plus_264": "SCC-707 Plus - 264 t/h",
}
SECADOR_COMBUSTIVEIS = {
    "cavaco": "Cavaco",
    "lenha": "Lenha",
}
SECADOR_VOLUMES = {
    "6_35": "6,35 m³",
    "13": "13 m³",
    "20": "20 m³",
}


def collect_secador_campos(form):
    modelo = (form.get("secador_modelo") or "").strip()
    fornalha = (form.get("secador_fornalha") or "sem").strip()
    combustivel = (form.get("secador_combustivel") or "").strip() if fornalha == "com" else ""
    alimentador = (form.get("secador_alimentador") or "sem").strip()
    volume = (form.get("secador_alimentador_volume") or "").strip() if alimentador == "com" else ""
    return {
        "modelo": modelo,
        "modelo_rotulo": SECADOR_MODELOS.get(modelo, modelo),
        "fornalha": fornalha,
        "combustivel": combustivel,
        "combustivel_rotulo": SECADOR_COMBUSTIVEIS.get(combustivel, ""),
        "alimentador": alimentador,
        "alimentador_volume": volume,
        "alimentador_volume_rotulo": SECADOR_VOLUMES.get(volume, ""),
    }


def resumo_silo_pulmao(campos):
    partes = [
        "Silo Pulmão Elevado",
        f"{campos.get('diametro')} ft",
        f"{campos.get('aneis')} anéis",
        f"{campos.get('ton')} Ton",
    ]
    if campos.get("sacas"):
        partes.append(f"{campos.get('sacas')} scs")
    termometria = campos.get("termometria_rotulo")
    if termometria and campos.get("termometria") != "sem":
        partes.append(termometria)
        if campos.get("termometria_pacote_rotulo"):
            partes.append(campos["termometria_pacote_rotulo"])
    if campos.get("sensor_nivel") == "sim":
        partes.append("Sensor de Nível")
    if campos.get("aeracao") == "sim":
        partes.append(f"Aeração {campos.get('aeracao_taxa')}")
    if campos.get("escada_rotulo"):
        partes.append(f"Escada {campos.get('escada_rotulo')}")
    if campos.get("alternar_escadas") == "sim":
        partes.append("Alternar escadas caracol e marinheiro")
    for extra in campos.get("escada_extras") or []:
        if extra.get("rotulo"):
            partes.append(extra["rotulo"])
    return " | ".join(partes)


SILO_TERMOMETRIA = {
    "sem": "Sem Termometria",
    "thermo_grain": "Thermo Grain",
    "digital_grain": "Digital Grain",
    "procer": "PROCER",
}
SILO_PACOTES = {
    "pacote_1": "Pacote 1",
    "pacote_2": "Pacote 2",
}
SILO_ESCADAS = {
    "marinheiro": "Marinheiro",
    "caracol": "Caracol",
}
SILO_EXTRAS = {
    "guarda_corpo_beiral": "Guarda corpo de beiral",
    "monovia_telhado": "Monovia do telhado",
    "pontos_ancoragem": "Pontos de ancoragem",
    "suporte_monope": "Suporte para monopé",
}


def collect_silo_pulmao_campos(form):
    termometria = (form.get("silo_termometria") or "sem").strip()
    pacote = (form.get("silo_termometria_pacote") or "").strip() if termometria != "sem" else ""
    aeracao = (form.get("silo_aeracao") or "").strip()
    escada = (form.get("silo_escada") or "").strip()
    extras = []
    for chave in form.getlist("silo_escada_extra"):
        if chave in SILO_EXTRAS:
            extras.append({"chave": chave, "rotulo": SILO_EXTRAS[chave]})
    return {
        "modo": (form.get("silo_modo") or "").strip(),
        "diametro": (form.get("silo_diametro") or "").strip(),
        "aneis": (form.get("silo_aneis") or "").strip(),
        "ton": (form.get("silo_ton") or "").strip(),
        "sacas": (form.get("silo_sacas") or "").strip(),
        "capacidade_tipo": (form.get("silo_capacidade_tipo") or "").strip(),
        "capacidade_desejada": (form.get("silo_capacidade_desejada") or "").strip(),
        "termometria": termometria,
        "termometria_rotulo": SILO_TERMOMETRIA.get(termometria, ""),
        "termometria_pacote": pacote,
        "termometria_pacote_rotulo": SILO_PACOTES.get(pacote, ""),
        "sensor_nivel": (form.get("silo_sensor_nivel") or "").strip(),
        "aeracao": aeracao,
        "aeracao_taxa": (form.get("silo_aeracao_taxa") or "").strip() if aeracao == "sim" else "",
        "escada": escada,
        "escada_rotulo": SILO_ESCADAS.get(escada, ""),
        "alternar_escadas": (form.get("silo_alternar_escadas") or "nao").strip(),
        "escada_extras": extras,
    }


TRANSPORTADOR_TIPOS = {
    "redler": "Redler",
    "correia": "Correia",
    "hi_flight": "Hi-Flight",
    "helicoidal": "Helicoidal",
    "elevador": "Elevador",
}
TRANSPORTADOR_SUBTIPOS = {
    "convencional": "Convencional",
    "reversivel": "Reversível",
    "enclausurada": "Enclausurada",
    "aberta": "Aberta",
    "aberta_nova": "Aberta Nova",
}
TRANSPORTADOR_ITENS = {
    "sensor_rotacao": {"nome": "Sensor de Rotação", "resumo": "Rotação", "categoria": "sensor"},
    "sensor_temperatura": {"nome": "Sensor de Temperatura", "resumo": "Temperatura", "categoria": "sensor"},
    "sensor_embuchamento": {"nome": "Sensor de Embuchamento", "resumo": "Embuchamento", "categoria": "sensor"},
    "sensor_desalinhamento": {"nome": "Sensor de Desalinhamento", "resumo": "Desalinhamento", "categoria": "sensor"},
    "janela_alivio_pressao": {"nome": "Janela de Alívio de Pressão", "resumo": "Janela de Alívio", "categoria": "acessorio"},
    "filtro_pontual": {"nome": "Filtro Pontual", "resumo": "Filtro Pontual", "categoria": "acessorio"},
    "modulo_alivio_pressao": {"nome": "Módulo de Alívio de Pressão", "resumo": "Módulo de Alívio", "categoria": "acessorio"},
    "pe_auto_limpante": {"nome": "Pé Auto-Limpante", "resumo": "Pé Auto-Limpante", "categoria": "acessorio"},
    "plataforma_valvula_2_vias": {
        "nome": "Plataforma p/ manutenção de válvula 2 vias",
        "resumo": "Plataforma válvula 2 vias",
        "categoria": "acessorio",
    },
}


def collect_transportador_campos(form):
    tipo = (form.get("transportador_tipo") or "").strip()
    subtipo = (form.get("transportador_subtipo") or "").strip()
    selecionados = form.getlist("transportador_item")
    itens = []
    for chave in selecionados:
        definicao = TRANSPORTADOR_ITENS.get(chave)
        if not definicao:
            continue
        item = dict(definicao)
        item["chave"] = chave
        item["observacao"] = (form.get(f"transportador_obs__{chave}") or "").strip()
        itens.append(item)
    return {
        "tipo": tipo,
        "tipo_rotulo": TRANSPORTADOR_TIPOS.get(tipo, tipo),
        "subtipo": subtipo,
        "subtipo_rotulo": TRANSPORTADOR_SUBTIPOS.get(subtipo, ""),
        "sensores_acessorios": itens,
    }


def carregar_opcoes_itens(conn, itens):
    for item in itens:
        opcoes = conn.execute(
            """
            SELECT * FROM itens_anteprojeto_opcoes
            WHERE item_anteprojeto_id = ?
            ORDER BY id
            """,
            (item["id"],),
        ).fetchall()
        item["opcoes"] = [dict(opcao) for opcao in opcoes]
        if item["equipamento_nome"] in ("Fluxo", "Item 1 - Fluxo"):
            item["equipamento_nome"] = "Fluxo"
            item["resumo_fluxo"] = resumo_fluxo(item["opcoes"])
        elif item["equipamento_nome"] in ("Transportador", "Item 2 - Transportadores"):
            item["equipamento_nome"] = "Transportador"
            item["resumo_transportador"] = resumo_transportador(item["campos"])
        elif item["equipamento_nome"] in (
            "Máquina de Limpeza Grain Cleaner EC",
            "Item 3 - Máquina de Limpeza Grain Cleaner EC",
        ):
            item["equipamento_nome"] = "Máquina de Limpeza Grain Cleaner EC"
            item["resumo_maquina_limpeza"] = resumo_maquina_limpeza(item["campos"])
        elif item["equipamento_nome"] in ("Secador Process Dryer", "Item 4 - Secadores Process Dryer"):
            item["equipamento_nome"] = "Secador Process Dryer"
            item["resumo_secador"] = resumo_secador(item["campos"])
        elif item["equipamento_nome"] in ("Silo Pulmão Elevado", "Item 5 - Silo Pulmão Elevado"):
            item["equipamento_nome"] = "Silo Pulmão Elevado"
            item["resumo_silo_pulmao"] = resumo_silo_pulmao(item["campos"])
    return itens


def opcoes_item_map(conn, item_id):
    opcoes = conn.execute(
        """
        SELECT opcao_id, valor, valor_rotulo
        FROM itens_anteprojeto_opcoes
        WHERE item_anteprojeto_id = ?
        """,
        (item_id,),
    ).fetchall()
    return {str(opcao["opcao_id"]): {"valor": opcao["valor"], "valor_rotulo": opcao["valor_rotulo"]} for opcao in opcoes}


def salvar_opcoes_item(conn, item_id, equipamento_id, form):
    conn.execute("DELETE FROM itens_anteprojeto_opcoes WHERE item_anteprojeto_id = ?", (item_id,))
    opcoes = obter_opcoes_disponiveis(conn, equipamento_id)
    for opcao in opcoes:
        present_name = f"opcao_presente__{opcao['id']}"
        field_name = f"opcao__{opcao['id']}"
        if form.get(present_name) != "1":
            continue
        valor = ""
        valor_rotulo = ""

        if opcao["tipo"] == "booleano":
            valor = "sim" if form.get(field_name) == "sim" else "nao"
            valor_rotulo = "Sim" if valor == "sim" else "Nao"
        else:
            valor = (form.get(field_name) or "").strip()
            if not valor and not opcao["obrigatorio"]:
                continue
            valor_rotulo = valor
            if opcao["tipo"] == "selecao":
                for alternativa in opcao["valores"]:
                    if alternativa["valor"] == valor:
                        valor_rotulo = alternativa["rotulo"]
                        break

        conn.execute(
            """
            INSERT INTO itens_anteprojeto_opcoes
            (item_anteprojeto_id, opcao_id, opcao_nome, opcao_chave, valor, valor_rotulo)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (item_id, opcao["id"], opcao["nome"], opcao["chave"], valor, valor_rotulo),
        )


def get_opcoes_cadastradas_equipamento(conn, equipamento_id):
    opcoes = conn.execute(
        """
        SELECT * FROM equipamentos_opcoes
        WHERE equipamento_id = ?
        ORDER BY ordem, nome, id
        """,
        (equipamento_id,),
    ).fetchall()
    resultado = []
    for opcao in opcoes:
        item = dict(opcao)
        valores = conn.execute(
            """
            SELECT valor, rotulo, ordem, ativo
            FROM equipamentos_opcoes_valores
            WHERE opcao_id = ?
            ORDER BY ordem, id
            """,
            (opcao["id"],),
        ).fetchall()
        item["valores"] = [dict(valor) for valor in valores if valor["ativo"]]
        item["valores_texto"] = "\n".join(
            f"{valor['valor']} | {valor['rotulo']}" if valor["valor"] != valor["rotulo"] else valor["rotulo"]
            for valor in valores
            if valor["ativo"]
        )
        dependencia = conn.execute(
            """
            SELECT o.chave AS depende_chave, d.depende_valor
            FROM equipamentos_opcoes_dependencias d
            JOIN equipamentos_opcoes o ON o.id = d.depende_opcao_id
            WHERE d.opcao_id = ?
            """,
            (opcao["id"],),
        ).fetchone()
        item["depende_chave"] = dependencia["depende_chave"] if dependencia else ""
        item["depende_valor"] = dependencia["depende_valor"] if dependencia else ""
        resultado.append(item)
    return resultado


def parse_opcao_valores(raw):
    valores = []
    for index, line in enumerate((raw or "").replace("\r", "").split("\n"), start=1):
        line = line.strip()
        if not line:
            continue
        if "|" in line:
            valor, rotulo = [part.strip() for part in line.split("|", 1)]
        else:
            rotulo = line
            valor = normalize_chave(line)
        if valor and rotulo:
            valores.append({"valor": valor, "rotulo": rotulo, "ordem": index})
    return valores


def opcoes_from_form(form):
    nomes = form.getlist("op_nome")
    chaves = form.getlist("op_chave")
    tipos = form.getlist("op_tipo")
    obrigatorios = set(form.getlist("op_obrigatorio"))
    ativos = set(form.getlist("op_ativo"))
    ordens = form.getlist("op_ordem")
    valores_texto = form.getlist("op_valores")
    depende_chaves = form.getlist("op_depende_chave")
    depende_valores = form.getlist("op_depende_valor")
    opcoes = []
    usadas = set()

    for index, nome in enumerate(nomes):
        nome = (nome or "").strip()
        if not nome:
            continue
        chave_base = (chaves[index] if index < len(chaves) else "").strip() or normalize_chave(nome)
        chave = normalize_chave(chave_base)
        original = chave
        suffix = 2
        while chave in usadas:
            chave = f"{original}_{suffix}"
            suffix += 1
        usadas.add(chave)

        tipo = tipos[index] if index < len(tipos) else "booleano"
        if tipo not in TIPOS_OPCAO_EQUIPAMENTO:
            tipo = "booleano"
        try:
            ordem = int(ordens[index]) if index < len(ordens) and ordens[index] else index + 1
        except ValueError:
            ordem = index + 1
        row_key = str(index)

        opcoes.append(
            {
                "nome": nome,
                "chave": chave,
                "tipo": tipo,
                "obrigatorio": 1 if row_key in obrigatorios else 0,
                "ativo": 1 if row_key in ativos else 0,
                "ordem": ordem,
                "valores": parse_opcao_valores(valores_texto[index] if index < len(valores_texto) else ""),
                "depende_chave": normalize_chave(depende_chaves[index]) if index < len(depende_chaves) and depende_chaves[index] else "",
                "depende_valor": (depende_valores[index] if index < len(depende_valores) else "").strip(),
            }
        )
    return opcoes


def salvar_opcoes_equipamento(conn, equipamento_id, opcoes):
    atuais = conn.execute(
        "SELECT id, chave FROM equipamentos_opcoes WHERE equipamento_id = ?",
        (equipamento_id,),
    ).fetchall()
    atuais_por_chave = {row["chave"]: row["id"] for row in atuais}
    ids_mantidos = set()
    ids_por_chave = {}

    for opcao in opcoes:
        opcao_id = atuais_por_chave.get(opcao["chave"])
        if opcao_id:
            conn.execute(
                """
                UPDATE equipamentos_opcoes
                SET nome = ?, tipo = ?, obrigatorio = ?, ordem = ?, ativo = ?
                WHERE id = ?
                """,
                (opcao["nome"], opcao["tipo"], opcao["obrigatorio"], opcao["ordem"], opcao["ativo"], opcao_id),
            )
        else:
            cur = conn.execute(
                """
                INSERT INTO equipamentos_opcoes
                (equipamento_id, nome, chave, tipo, obrigatorio, ordem, ativo)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    equipamento_id,
                    opcao["nome"],
                    opcao["chave"],
                    opcao["tipo"],
                    opcao["obrigatorio"],
                    opcao["ordem"],
                    opcao["ativo"],
                ),
            )
            opcao_id = cur.lastrowid
        ids_mantidos.add(opcao_id)
        ids_por_chave[opcao["chave"]] = opcao_id

        conn.execute("DELETE FROM equipamentos_opcoes_valores WHERE opcao_id = ?", (opcao_id,))
        for valor in opcao["valores"]:
            conn.execute(
                """
                INSERT INTO equipamentos_opcoes_valores
                (opcao_id, valor, rotulo, ordem, ativo)
                VALUES (?, ?, ?, ?, ?)
                """,
                (opcao_id, valor["valor"], valor["rotulo"], valor["ordem"], 1),
            )

    for row in atuais:
        if row["id"] in ids_mantidos:
            continue
        total_usos = conn.execute(
            "SELECT COUNT(*) FROM itens_anteprojeto_opcoes WHERE opcao_id = ?",
            (row["id"],),
        ).fetchone()[0]
        if total_usos:
            conn.execute("UPDATE equipamentos_opcoes SET ativo = 0 WHERE id = ?", (row["id"],))
        else:
            conn.execute("DELETE FROM equipamentos_opcoes WHERE id = ?", (row["id"],))

    for opcao_id in ids_mantidos:
        conn.execute(
            "DELETE FROM equipamentos_opcoes_dependencias WHERE opcao_id = ? OR depende_opcao_id = ?",
            (opcao_id, opcao_id),
        )

    for opcao in opcoes:
        opcao_id = ids_por_chave.get(opcao["chave"])
        depende_id = ids_por_chave.get(opcao["depende_chave"])
        if opcao_id and depende_id and opcao_id != depende_id and opcao["depende_valor"]:
            conn.execute(
                """
                INSERT OR REPLACE INTO equipamentos_opcoes_dependencias
                (opcao_id, depende_opcao_id, depende_valor)
                VALUES (?, ?, ?)
                """,
                (opcao_id, depende_id, opcao["depende_valor"]),
            )


def normalize_equipamento_schema(nome, campos):
    normalizados = []
    for ordem, campo in enumerate(campos, start=1):
        campo_nome = (campo.get("nome") or "").strip()
        campo_tipo = (campo.get("tipo") or "text").strip()
        if not campo_nome or campo_tipo not in TIPOS_CAMPO_EQUIPAMENTO:
            continue

        novo = {
            "nome": campo_nome,
            "tipo": campo_tipo,
            "obrigatorio": bool(campo.get("obrigatorio")),
            "ordem": int(campo.get("ordem") or ordem),
        }

        if campo_tipo in ("select", "checkbox"):
            opcoes = campo.get("opcoes") or []
            if isinstance(opcoes, str):
                opcoes = [opcao.strip() for opcao in opcoes.replace("\r", "").replace(",", "\n").split("\n")]
            novo["opcoes"] = [opcao for opcao in opcoes if opcao]
        elif campo_tipo == "info":
            novo["texto"] = (campo.get("texto") or campo.get("opcoes") or "").strip()

        normalizados.append(novo)

    normalizados.sort(key=lambda item: item.get("ordem", 0))
    return {"nome": nome.strip(), "campos": normalizados}


def equipamento_from_form(form):
    nomes = form.getlist("field_nome")
    tipos = form.getlist("field_tipo")
    opcoes = form.getlist("field_opcoes")
    obrigatorios = form.getlist("field_obrigatorio")
    ordens = form.getlist("field_ordem")
    campos = []

    for index, nome in enumerate(nomes):
        campos.append(
            {
                "nome": nome,
                "tipo": tipos[index] if index < len(tipos) else "text",
                "opcoes": opcoes[index] if index < len(opcoes) else "",
                "texto": opcoes[index] if index < len(opcoes) else "",
                "obrigatorio": (obrigatorios[index] if index < len(obrigatorios) else "nao") == "sim",
                "ordem": ordens[index] if index < len(ordens) else index + 1,
            }
        )

    return normalize_equipamento_schema(form.get("nome") or "", campos)


def equipamento_basico_from_form(form):
    parent_id = form.get("parent_id")
    return {
        "parent_id": int(parent_id) if parent_id else None,
        "nome": (form.get("nome") or "").strip(),
        "descricao": (form.get("descricao") or "").strip(),
        "categoria": (form.get("categoria") or "").strip(),
        "subcategoria": (form.get("subcategoria") or "").strip(),
        "fabricante": (form.get("fabricante") or "").strip(),
        "modelo": (form.get("modelo") or "").strip(),
        "ativo": 1 if form.get("ativo") == "1" else 0,
    }


def atributos_from_form(form):
    nomes = form.getlist("attr_nome")
    chaves = form.getlist("attr_chave")
    tipos = form.getlist("attr_tipo")
    valores = form.getlist("attr_valor")
    unidades = form.getlist("attr_unidade")
    ordens = form.getlist("attr_ordem")
    obrigatorios = set(form.getlist("attr_obrigatorio"))
    visiveis = set(form.getlist("attr_visivel_resumo"))
    atributos = []
    usadas = set()

    for index, nome in enumerate(nomes):
        nome = (nome or "").strip()
        if not nome:
            continue

        chave_base = (chaves[index] if index < len(chaves) else "").strip() or normalize_chave(nome)
        chave = normalize_chave(chave_base)
        original = chave
        suffix = 2
        while chave in usadas:
            chave = f"{original}_{suffix}"
            suffix += 1
        usadas.add(chave)

        tipo = tipos[index] if index < len(tipos) else "texto"
        if tipo not in TIPOS_ATRIBUTO_EQUIPAMENTO:
            tipo = "texto"

        try:
            ordem = int(ordens[index]) if index < len(ordens) and ordens[index] else index + 1
        except ValueError:
            ordem = index + 1

        row_key = str(index)
        atributos.append(
            {
                "nome": nome,
                "chave": chave,
                "tipo": tipo,
                "valor": (valores[index] if index < len(valores) else "").strip(),
                "unidade": (unidades[index] if index < len(unidades) else "").strip(),
                "ordem": ordem,
                "obrigatorio": 1 if row_key in obrigatorios else 0,
                "visivel_resumo": 1 if row_key in visiveis else 0,
            }
        )

    return atributos


def salvar_atributos_equipamento(conn, equipamento_id, atributos):
    conn.execute("DELETE FROM equipamentos_atributos WHERE equipamento_id = ?", (equipamento_id,))
    for atributo in atributos:
        conn.execute(
            """
            INSERT INTO equipamentos_atributos
            (equipamento_id, nome, chave, tipo, valor, unidade, ordem, obrigatorio, visivel_resumo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                equipamento_id,
                atributo["nome"],
                atributo["chave"],
                atributo["tipo"],
                atributo["valor"],
                atributo["unidade"],
                atributo["ordem"],
                atributo["obrigatorio"],
                atributo["visivel_resumo"],
            ),
        )


def unique_name(conn, table, base_name):
    name = base_name
    suffix = 2
    while conn.execute(f"SELECT 1 FROM {table} WHERE nome = ?", (name,)).fetchone():
        name = f"{base_name} {suffix}"
        suffix += 1
    return name


def usuario_form_data(form):
    return {
        "nome": (form.get("nome") or "").strip(),
        "usuario": (form.get("usuario") or "").strip(),
        "senha": form.get("senha") or "",
        "is_admin": 1 if form.get("is_admin") == "1" else 0,
        "ativo": 1 if form.get("ativo") == "1" else 0,
    }


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "erro": None})


@app.post("/login")
def login(request: Request, usuario: Annotated[str, Form()], senha: Annotated[str, Form()]):
    usuario_row = autenticar_usuario(usuario.strip(), senha)
    if not usuario_row:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "erro": "Usuario ou senha invalidos."},
            status_code=401,
        )

    request.session["usuario_id"] = usuario_row["id"]
    request.session["usuario_nome"] = usuario_row["nome"]
    request.session["usuario"] = usuario_row["usuario"]
    request.session["is_admin"] = usuario_row["is_admin"]
    return RedirectResponse("/", status_code=303)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    usuario = exigir_login(request)
    if isinstance(usuario, RedirectResponse):
        return usuario
    with get_conn() as conn:
        anteprojetos = conn.execute(
            "SELECT * FROM anteprojetos ORDER BY updated_at DESC, id DESC"
        ).fetchall()
    return templates.TemplateResponse("index.html", {"request": request, "anteprojetos": anteprojetos})


@app.post("/anteprojetos/{anteprojeto_id}/duplicar")
def duplicar_anteprojeto(request: Request, anteprojeto_id: int):
    usuario = exigir_login(request)
    if isinstance(usuario, RedirectResponse):
        return usuario
    with get_conn() as conn:
        anteprojeto = get_anteprojeto_or_404(conn, anteprojeto_id)
        cur = conn.execute(
            """
            INSERT INTO anteprojetos
            (cliente, obra_local, tipo_obra, responsavel, observacoes_gerais, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                f"{anteprojeto['cliente']} - Copia",
                anteprojeto["obra_local"],
                anteprojeto["tipo_obra"],
                anteprojeto["responsavel"],
                anteprojeto["observacoes_gerais"],
                "Rascunho",
            ),
        )
        novo_id = cur.lastrowid
        itens = conn.execute(
            "SELECT * FROM itens_anteprojeto WHERE anteprojeto_id = ? ORDER BY id",
            (anteprojeto_id,),
        ).fetchall()
        for item in itens:
            conn.execute(
                """
                INSERT INTO itens_anteprojeto
                (anteprojeto_id, equipamento_modelo_id, equipamento_nome, quantidade,
                 tipo_definicao, situacao, campos_json, observacao_inicial, retorno_engenharia)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    novo_id,
                    item["equipamento_modelo_id"],
                    item["equipamento_nome"],
                    item["quantidade"],
                    item["tipo_definicao"],
                    item["situacao"],
                    item["campos_json"],
                    item["observacao_inicial"],
                    item["retorno_engenharia"],
                ),
            )
        registrar_historico_anteprojeto(
            conn,
            novo_id,
            usuario,
            "criacao",
            f"Anteprojeto duplicado a partir do #{anteprojeto_id}",
        )
        criar_versao_anteprojeto(conn, novo_id, usuario, "Versao inicial da copia")
    return RedirectResponse(f"/anteprojetos/{novo_id}", status_code=303)


@app.post("/anteprojetos/{anteprojeto_id}/excluir")
def excluir_anteprojeto(request: Request, anteprojeto_id: int):
    usuario = exigir_login(request)
    if isinstance(usuario, RedirectResponse):
        return usuario
    with get_conn() as conn:
        get_anteprojeto_or_404(conn, anteprojeto_id)
        conn.execute("DELETE FROM anteprojetos WHERE id = ?", (anteprojeto_id,))
    return RedirectResponse("/", status_code=303)


@app.get("/equipamentos", response_class=HTMLResponse)
def equipamentos_index(request: Request):
    usuario = exigir_login(request)
    if isinstance(usuario, RedirectResponse):
        return usuario
    with get_conn() as conn:
        equipamentos_rows = conn.execute(
            "SELECT * FROM equipamentos_modelo ORDER BY ativo DESC, nome"
        ).fetchall()
        equipamentos = []
        for row in equipamentos_rows:
            equipamento = dict(row)
            atributos = get_atributos_equipamento(conn, row["id"], somente_resumo=True)
            equipamento["atributos_resumo"] = [formatar_atributo_resumo(attr) for attr in atributos]
            equipamento["caminho"] = obter_caminho_equipamento(conn, row["id"])
            equipamento["tem_filhos"] = has_filhos_equipamento(conn, row["id"])
            equipamentos.append(equipamento)
        equipamentos_arvore = montar_arvore_equipamentos(equipamentos)
    return templates.TemplateResponse(
        "equipamentos_index.html",
        {
            "request": request,
            "equipamentos": equipamentos,
            "equipamentos_arvore": equipamentos_arvore,
            "usuario": usuario,
        },
    )


@app.post("/equipamentos/zerar")
def zerar_equipamentos(request: Request):
    usuario = exigir_admin(request)
    if isinstance(usuario, RedirectResponse):
        return usuario
    with get_conn() as conn:
        total_usos = conn.execute("SELECT COUNT(*) FROM itens_anteprojeto").fetchone()[0]
        if total_usos:
            raise HTTPException(
                status_code=400,
                detail="Existem itens de anteprojeto usando equipamentos. Remova esses itens antes de zerar os cadastros.",
            )
        conn.execute("DELETE FROM equipamentos_atributos")
        conn.execute("UPDATE equipamentos_modelo SET parent_id = NULL")
        conn.execute("DELETE FROM equipamentos_modelo")
        conn.execute(
            "DELETE FROM sqlite_sequence WHERE name IN ('equipamentos_atributos', 'equipamentos_modelo')"
        )
    return RedirectResponse("/equipamentos", status_code=303)


@app.get("/usuarios", response_class=HTMLResponse)
def usuarios_index(request: Request):
    usuario = exigir_admin(request)
    if isinstance(usuario, RedirectResponse):
        return usuario
    with get_conn() as conn:
        usuarios = conn.execute(
            "SELECT id, nome, usuario, is_admin, ativo, criado_em FROM usuarios ORDER BY ativo DESC, nome"
        ).fetchall()
    return templates.TemplateResponse(
        "usuarios_index.html",
        {"request": request, "usuarios": usuarios},
    )


@app.get("/usuarios/novo", response_class=HTMLResponse)
def novo_usuario(request: Request):
    usuario = exigir_admin(request)
    if isinstance(usuario, RedirectResponse):
        return usuario
    return templates.TemplateResponse(
        "usuario_form.html",
        {"request": request, "usuario_editando": None, "erro": None},
    )


@app.post("/usuarios")
async def criar_usuario(request: Request):
    usuario = exigir_admin(request)
    if isinstance(usuario, RedirectResponse):
        return usuario
    form = await request.form()
    dados = usuario_form_data(form)

    if not dados["nome"] or not dados["usuario"] or not dados["senha"]:
        return templates.TemplateResponse(
            "usuario_form.html",
            {
                "request": request,
                "usuario_editando": None,
                "erro": "Nome, usuario e senha sao obrigatorios.",
            },
            status_code=400,
        )

    with get_conn() as conn:
        existente = conn.execute(
            "SELECT id FROM usuarios WHERE usuario = ?",
            (dados["usuario"],),
        ).fetchone()
        if existente:
            return templates.TemplateResponse(
                "usuario_form.html",
                {
                    "request": request,
                    "usuario_editando": None,
                    "erro": "Ja existe um usuario com esse login.",
                },
                status_code=400,
            )
        cur = conn.execute(
            """
            INSERT INTO usuarios (nome, usuario, senha_hash, is_admin, ativo)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                dados["nome"],
                dados["usuario"],
                hash_senha(dados["senha"]),
                dados["is_admin"],
                dados["ativo"],
            ),
        )
    return RedirectResponse(f"/usuarios/{cur.lastrowid}/editar", status_code=303)


@app.get("/usuarios/{usuario_id}/editar", response_class=HTMLResponse)
def editar_usuario(request: Request, usuario_id: int):
    usuario = exigir_admin(request)
    if isinstance(usuario, RedirectResponse):
        return usuario
    with get_conn() as conn:
        usuario_editando = conn.execute(
            "SELECT id, nome, usuario, is_admin, ativo, criado_em FROM usuarios WHERE id = ?",
            (usuario_id,),
        ).fetchone()
        if not usuario_editando:
            raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    return templates.TemplateResponse(
        "usuario_form.html",
        {"request": request, "usuario_editando": usuario_editando, "erro": None},
    )


@app.post("/usuarios/{usuario_id}")
async def atualizar_usuario(request: Request, usuario_id: int):
    usuario = exigir_admin(request)
    if isinstance(usuario, RedirectResponse):
        return usuario
    form = await request.form()
    dados = usuario_form_data(form)

    if not dados["nome"] or not dados["usuario"]:
        with get_conn() as conn:
            usuario_editando = conn.execute(
                "SELECT id, nome, usuario, is_admin, ativo, criado_em FROM usuarios WHERE id = ?",
                (usuario_id,),
            ).fetchone()
        return templates.TemplateResponse(
            "usuario_form.html",
            {
                "request": request,
                "usuario_editando": usuario_editando,
                "erro": "Nome e usuario sao obrigatorios.",
            },
            status_code=400,
        )

    with get_conn() as conn:
        usuario_editando = conn.execute(
            "SELECT * FROM usuarios WHERE id = ?",
            (usuario_id,),
        ).fetchone()
        if not usuario_editando:
            raise HTTPException(status_code=404, detail="Usuario nao encontrado")

        existente = conn.execute(
            "SELECT id FROM usuarios WHERE usuario = ? AND id <> ?",
            (dados["usuario"], usuario_id),
        ).fetchone()
        if existente:
            return templates.TemplateResponse(
                "usuario_form.html",
                {
                    "request": request,
                    "usuario_editando": usuario_editando,
                    "erro": "Ja existe outro usuario com esse login.",
                },
                status_code=400,
            )

        conn.execute(
            """
            UPDATE usuarios
            SET nome = ?, usuario = ?, is_admin = ?, ativo = ?
            WHERE id = ?
            """,
            (dados["nome"], dados["usuario"], dados["is_admin"], dados["ativo"], usuario_id),
        )
        if dados["senha"]:
            conn.execute(
                "UPDATE usuarios SET senha_hash = ? WHERE id = ?",
                (hash_senha(dados["senha"]), usuario_id),
            )

        if usuario["id"] == usuario_id:
            request.session["usuario_nome"] = dados["nome"]
            request.session["usuario"] = dados["usuario"]
            request.session["is_admin"] = dados["is_admin"]
            if not dados["ativo"]:
                request.session.clear()
                return RedirectResponse("/login", status_code=303)

    return RedirectResponse(f"/usuarios/{usuario_id}/editar", status_code=303)


@app.post("/usuarios/{usuario_id}/alternar-status")
def alternar_status_usuario(request: Request, usuario_id: int):
    usuario = exigir_admin(request)
    if isinstance(usuario, RedirectResponse):
        return usuario
    with get_conn() as conn:
        usuario_editando = conn.execute(
            "SELECT ativo FROM usuarios WHERE id = ?",
            (usuario_id,),
        ).fetchone()
        if not usuario_editando:
            raise HTTPException(status_code=404, detail="Usuario nao encontrado")
        novo_status = 0 if usuario_editando["ativo"] else 1
        conn.execute("UPDATE usuarios SET ativo = ? WHERE id = ?", (novo_status, usuario_id))

    if usuario["id"] == usuario_id and novo_status == 0:
        request.session.clear()
        return RedirectResponse("/login", status_code=303)
    return RedirectResponse("/usuarios", status_code=303)


@app.get("/equipamentos/novo", response_class=HTMLResponse)
def novo_equipamento(request: Request, parent_id: int | None = None):
    usuario = exigir_admin(request)
    if isinstance(usuario, RedirectResponse):
        return usuario
    with get_conn() as conn:
        parent_id_selecionado = None
        if parent_id:
            parent = conn.execute(
                "SELECT id FROM equipamentos_modelo WHERE id = ?",
                (parent_id,),
            ).fetchone()
            if parent:
                parent_id_selecionado = parent_id
        equipamentos_pai = get_opcoes_pai_equipamento(conn)
    return templates.TemplateResponse(
        "equipamento_form.html",
        {
            "request": request,
            "equipamento": None,
            "atributos": [],
            "equipamentos_pai": equipamentos_pai,
            "parent_id_selecionado": parent_id_selecionado,
            "tipos_atributo": TIPOS_ATRIBUTO_EQUIPAMENTO,
            "opcoes_equipamento": [],
            "tipos_opcao": TIPOS_OPCAO_EQUIPAMENTO,
        },
    )


@app.get("/equipamentos/{equipamento_id}/filhos")
def filhos_equipamento(request: Request, equipamento_id: int):
    usuario = exigir_login(request)
    if isinstance(usuario, RedirectResponse):
        return usuario
    with get_conn() as conn:
        filhos = conn.execute(
            """
            SELECT id, nome
            FROM equipamentos_modelo
            WHERE parent_id = ? AND ativo = 1
            ORDER BY id
            """,
            (equipamento_id,),
        ).fetchall()
    return [{"id": row["id"], "nome": row["nome"]} for row in filhos]


@app.get("/equipamentos/{equipamento_id}/atributos")
def atributos_equipamento(request: Request, equipamento_id: int):
    usuario = exigir_login(request)
    if isinstance(usuario, RedirectResponse):
        return usuario
    with get_conn() as conn:
        atributos = conn.execute(
            """
            SELECT nome, chave, tipo, valor, unidade
            FROM equipamentos_atributos
            WHERE equipamento_id = ?
            ORDER BY ordem, nome, id
            """,
            (equipamento_id,),
        ).fetchall()
    return [dict(row) for row in atributos]


@app.get("/equipamentos/{equipamento_id}/opcoes")
def opcoes_equipamento(request: Request, equipamento_id: int):
    usuario = exigir_login(request)
    if isinstance(usuario, RedirectResponse):
        return usuario
    with get_conn() as conn:
        opcoes = obter_opcoes_disponiveis(conn, equipamento_id)
    return [
        {
            "id": opcao["id"],
            "nome": opcao["nome"],
            "chave": opcao["chave"],
            "tipo": opcao["tipo"],
            "obrigatorio": opcao["obrigatorio"],
            "valores": opcao["valores"],
            "dependencia": opcao["dependencia"],
        }
        for opcao in opcoes
    ]


@app.get("/equipamentos/{equipamento_id}", response_class=HTMLResponse)
def visualizar_equipamento(request: Request, equipamento_id: int):
    usuario = exigir_login(request)
    if isinstance(usuario, RedirectResponse):
        return usuario
    with get_conn() as conn:
        equipamento = conn.execute(
            "SELECT * FROM equipamentos_modelo WHERE id = ?",
            (equipamento_id,),
        ).fetchone()
        if not equipamento:
            raise HTTPException(status_code=404, detail="Equipamento nao encontrado")
        atributos = get_atributos_equipamento(conn, equipamento_id, somente_resumo=True)
        caminho = obter_caminho_equipamento(conn, equipamento_id)
    return templates.TemplateResponse(
        "equipamento_detalhe.html",
        {
            "request": request,
            "equipamento": equipamento,
            "atributos": atributos,
            "caminho": caminho,
            "usuario": usuario,
        },
    )


@app.post("/equipamentos")
async def criar_equipamento(request: Request):
    usuario = exigir_admin(request)
    if isinstance(usuario, RedirectResponse):
        return usuario
    form = await request.form()
    dados = equipamento_basico_from_form(form)
    if not dados["nome"]:
        raise HTTPException(status_code=400, detail="Nome do equipamento e obrigatorio")

    schema = normalize_equipamento_schema(dados["nome"], [])
    atributos = atributos_from_form(form)
    opcoes = opcoes_from_form(form)
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO equipamentos_modelo
            (parent_id, nome, descricao, categoria, subcategoria, fabricante, modelo, schema_json, ativo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dados["parent_id"],
                dados["nome"],
                dados["descricao"],
                dados["categoria"],
                dados["subcategoria"],
                dados["fabricante"],
                dados["modelo"],
                json.dumps(schema, ensure_ascii=False),
                dados["ativo"],
            ),
        )
        salvar_atributos_equipamento(conn, cur.lastrowid, atributos)
        salvar_opcoes_equipamento(conn, cur.lastrowid, opcoes)
    return RedirectResponse(f"/equipamentos/{cur.lastrowid}/editar", status_code=303)


@app.get("/equipamentos/{equipamento_id}/editar", response_class=HTMLResponse)
def editar_equipamento(request: Request, equipamento_id: int):
    usuario = exigir_admin(request)
    if isinstance(usuario, RedirectResponse):
        return usuario
    with get_conn() as conn:
        equipamento = conn.execute(
            "SELECT * FROM equipamentos_modelo WHERE id = ?", (equipamento_id,)
        ).fetchone()
        if not equipamento:
            raise HTTPException(status_code=404, detail="Equipamento nao encontrado")
        atributos = get_atributos_equipamento(conn, equipamento_id)
        equipamentos_pai = get_opcoes_pai_equipamento(conn, equipamento_id)
        opcoes_equipamento = get_opcoes_cadastradas_equipamento(conn, equipamento_id)
    return templates.TemplateResponse(
        "equipamento_form.html",
        {
            "request": request,
            "equipamento": equipamento,
            "atributos": atributos,
            "equipamentos_pai": equipamentos_pai,
            "parent_id_selecionado": equipamento["parent_id"],
            "tipos_atributo": TIPOS_ATRIBUTO_EQUIPAMENTO,
            "opcoes_equipamento": opcoes_equipamento,
            "tipos_opcao": TIPOS_OPCAO_EQUIPAMENTO,
        },
    )


@app.post("/equipamentos/{equipamento_id}")
async def atualizar_equipamento(request: Request, equipamento_id: int):
    usuario = exigir_admin(request)
    if isinstance(usuario, RedirectResponse):
        return usuario
    form = await request.form()
    dados = equipamento_basico_from_form(form)
    if not dados["nome"]:
        raise HTTPException(status_code=400, detail="Nome do equipamento e obrigatorio")

    atributos = atributos_from_form(form)
    opcoes = opcoes_from_form(form)
    with get_conn() as conn:
        equipamento = conn.execute(
            "SELECT id FROM equipamentos_modelo WHERE id = ?", (equipamento_id,)
        ).fetchone()
        if not equipamento:
            raise HTTPException(status_code=404, detail="Equipamento nao encontrado")
        if dados["parent_id"] == equipamento_id or dados["parent_id"] in obter_descendentes_equipamento(conn, equipamento_id):
            raise HTTPException(status_code=400, detail="Equipamento pai invalido")
        conn.execute(
            """
            UPDATE equipamentos_modelo
            SET parent_id = ?, nome = ?, descricao = ?, categoria = ?, subcategoria = ?,
                fabricante = ?, modelo = ?, ativo = ?, atualizado_em = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                dados["parent_id"],
                dados["nome"],
                dados["descricao"],
                dados["categoria"],
                dados["subcategoria"],
                dados["fabricante"],
                dados["modelo"],
                dados["ativo"],
                equipamento_id,
            ),
        )
        salvar_atributos_equipamento(conn, equipamento_id, atributos)
        salvar_opcoes_equipamento(conn, equipamento_id, opcoes)
    return RedirectResponse(f"/equipamentos/{equipamento_id}/editar", status_code=303)


@app.post("/equipamentos/{equipamento_id}/duplicar")
def duplicar_equipamento(request: Request, equipamento_id: int):
    usuario = exigir_admin(request)
    if isinstance(usuario, RedirectResponse):
        return usuario
    with get_conn() as conn:
        equipamento = conn.execute(
            "SELECT * FROM equipamentos_modelo WHERE id = ?", (equipamento_id,)
        ).fetchone()
        if not equipamento:
            raise HTTPException(status_code=404, detail="Equipamento nao encontrado")
        if has_filhos_equipamento(conn, equipamento_id):
            raise HTTPException(status_code=400, detail="Selecione um modelo final da arvore.")

        schema = json.loads(equipamento["schema_json"])
        novo_nome = unique_name(conn, "equipamentos_modelo", f"{equipamento['nome']} - Copia")
        schema["nome"] = novo_nome
        cur = conn.execute(
            """
            INSERT INTO equipamentos_modelo
            (parent_id, nome, descricao, categoria, subcategoria, fabricante, modelo, schema_json, ativo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                equipamento["parent_id"],
                novo_nome,
                equipamento["descricao"],
                equipamento["categoria"],
                equipamento["subcategoria"],
                equipamento["fabricante"],
                equipamento["modelo"],
                json.dumps(schema, ensure_ascii=False),
                equipamento["ativo"],
            ),
        )
        atributos = get_atributos_equipamento(conn, equipamento_id)
        salvar_atributos_equipamento(conn, cur.lastrowid, [dict(attr) for attr in atributos])
        opcoes = get_opcoes_cadastradas_equipamento(conn, equipamento_id)
        salvar_opcoes_equipamento(conn, cur.lastrowid, opcoes)
    return RedirectResponse(f"/equipamentos/{cur.lastrowid}/editar", status_code=303)


@app.post("/equipamentos/{equipamento_id}/inativar")
def inativar_equipamento(request: Request, equipamento_id: int):
    usuario = exigir_admin(request)
    if isinstance(usuario, RedirectResponse):
        return usuario
    with get_conn() as conn:
        equipamento = conn.execute(
            "SELECT ativo FROM equipamentos_modelo WHERE id = ?", (equipamento_id,)
        ).fetchone()
        if not equipamento:
            raise HTTPException(status_code=404, detail="Equipamento nao encontrado")
        novo_status = 0 if equipamento["ativo"] else 1
        conn.execute(
            "UPDATE equipamentos_modelo SET ativo = ? WHERE id = ?",
            (novo_status, equipamento_id),
        )
    return RedirectResponse("/equipamentos", status_code=303)


@app.post("/equipamentos/{equipamento_id}/excluir")
def excluir_equipamento(request: Request, equipamento_id: int):
    usuario = exigir_admin(request)
    if isinstance(usuario, RedirectResponse):
        return usuario
    with get_conn() as conn:
        equipamento = conn.execute(
            "SELECT id FROM equipamentos_modelo WHERE id = ?", (equipamento_id,)
        ).fetchone()
        if not equipamento:
            raise HTTPException(status_code=404, detail="Equipamento nao encontrado")
        if has_filhos_equipamento(conn, equipamento_id):
            raise HTTPException(
                status_code=400,
                detail="Este equipamento possui filhos. Remova ou mova os filhos antes de excluir.",
            )

        total_usos = conn.execute(
            "SELECT COUNT(*) FROM itens_anteprojeto WHERE equipamento_modelo_id = ?",
            (equipamento_id,),
        ).fetchone()[0]
        if total_usos:
            raise HTTPException(
                status_code=400,
                detail="Este equipamento ja esta em uso em anteprojetos. Inative em vez de excluir.",
            )

        conn.execute("DELETE FROM equipamentos_modelo WHERE id = ?", (equipamento_id,))
    return RedirectResponse("/equipamentos", status_code=303)


@app.get("/anteprojetos/novo", response_class=HTMLResponse)
def novo_anteprojeto(request: Request):
    usuario = exigir_login(request)
    if isinstance(usuario, RedirectResponse):
        return usuario
    return templates.TemplateResponse(
        "anteprojeto_form.html",
        {
            "request": request,
            "anteprojeto": None,
            "status_opcoes": STATUS_OPCOES,
            "tipo_obra_opcoes": TIPO_OBRA_OPCOES,
        },
    )


@app.post("/anteprojetos")
def criar_anteprojeto(
    request: Request,
    cliente: Annotated[str, Form()],
    obra_local: Annotated[str, Form()],
    tipo_obra: Annotated[str, Form()],
    responsavel: Annotated[str, Form()],
    observacoes_gerais: Annotated[str, Form()] = "",
    status: Annotated[str, Form()] = "Rascunho",
):
    usuario = exigir_login(request)
    if isinstance(usuario, RedirectResponse):
        return usuario
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO anteprojetos
            (cliente, obra_local, tipo_obra, responsavel, observacoes_gerais, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (cliente, obra_local, tipo_obra, responsavel, observacoes_gerais, status),
        )
        anteprojeto_id = cur.lastrowid
        registrar_historico_anteprojeto(
            conn,
            anteprojeto_id,
            usuario,
            "criacao",
            "Anteprojeto criado",
        )
        criar_versao_anteprojeto(conn, anteprojeto_id, usuario, "Versao inicial")
    return RedirectResponse(f"/anteprojetos/{anteprojeto_id}", status_code=303)


@app.get("/anteprojetos/{anteprojeto_id}", response_class=HTMLResponse)
def editar_anteprojeto(
    request: Request,
    anteprojeto_id: int,
    item_id: int | None = None,
    retorno_item_id: int | None = None,
):
    usuario = exigir_login(request)
    if isinstance(usuario, RedirectResponse):
        return usuario
    with get_conn() as conn:
        anteprojeto = get_anteprojeto_or_404(conn, anteprojeto_id)
        produtos_pai = conn.execute(
            """
            SELECT
                id,
                CASE
                    WHEN nome = 'Item 1 - Fluxo' THEN 'Fluxo'
                    WHEN nome = 'Item 2 - Transportadores' THEN 'Transportadores'
                    WHEN nome = 'Item 3 - Máquina de Limpeza Grain Cleaner EC' THEN 'Máquina de Limpeza Grain Cleaner EC'
                    WHEN nome = 'Item 4 - Secadores Process Dryer' THEN 'Secadores Process Dryer'
                    WHEN nome = 'Item 5 - Silo Pulmão Elevado' THEN 'Silo Pulmão Elevado'
                    ELSE nome
                END AS nome,
                nome AS cadastro_nome
            FROM equipamentos_modelo
            WHERE parent_id IS NULL AND ativo = 1
            ORDER BY nome, id
            """
        ).fetchall()
        itens_rows = conn.execute(
            """
            SELECT * FROM itens_anteprojeto
            WHERE anteprojeto_id = ?
            ORDER BY tipo_definicao, equipamento_nome, id
            """,
            (anteprojeto_id,),
        ).fetchall()
        itens = carregar_opcoes_itens(conn, [parse_item(row) for row in itens_rows])
        itens_por_tipo = {tipo: [] for tipo in TIPO_DEFINICAO_OPCOES}
        for item in itens:
            itens_por_tipo.setdefault(item["tipo_definicao"], []).append(item)

        item_editando = None
        item_editando_cadeia = []
        item_editando_opcoes = {}
        if item_id:
            item_editando = conn.execute(
                "SELECT * FROM itens_anteprojeto WHERE id = ? AND anteprojeto_id = ?",
                (item_id, anteprojeto_id),
            ).fetchone()
            if item_editando:
                item_editando_cadeia = obter_cadeia_equipamento(conn, item_editando["equipamento_modelo_id"])
                item_editando_opcoes = opcoes_item_map(conn, item_editando["id"])
        retorno_item = None
        if retorno_item_id:
            retorno_item = conn.execute(
                "SELECT * FROM itens_anteprojeto WHERE id = ? AND anteprojeto_id = ?",
                (retorno_item_id, anteprojeto_id),
            ).fetchone()
        historico = conn.execute(
            """
            SELECT * FROM historico_anteprojeto
            WHERE anteprojeto_id = ?
            ORDER BY criado_em DESC, id DESC
            """,
            (anteprojeto_id,),
        ).fetchall()
        versoes = conn.execute(
            """
            SELECT id, numero_versao, usuario_nome, motivo, criado_em
            FROM versoes_anteprojeto
            WHERE anteprojeto_id = ?
            ORDER BY numero_versao DESC
            """,
            (anteprojeto_id,),
        ).fetchall()

    return templates.TemplateResponse(
        "anteprojeto_edit.html",
        {
            "request": request,
            "anteprojeto": anteprojeto,
            "produtos_pai": produtos_pai,
            "itens": itens,
            "itens_por_tipo": itens_por_tipo,
            "item_editando": item_editando,
            "item_editando_cadeia": item_editando_cadeia,
            "item_editando_opcoes": item_editando_opcoes,
            "item_editando_campos": json.loads(item_editando["campos_json"]) if item_editando else {},
            "retorno_item": retorno_item,
            "historico": historico,
            "versoes": versoes,
            "status_opcoes": STATUS_OPCOES,
            "tipo_obra_opcoes": TIPO_OBRA_OPCOES,
            "tipo_definicao_opcoes": TIPO_DEFINICAO_OPCOES,
            "situacao_reforma_opcoes": SITUACAO_REFORMA_OPCOES,
        },
    )


@app.post("/anteprojetos/{anteprojeto_id}")
def atualizar_anteprojeto(
    request: Request,
    anteprojeto_id: int,
    cliente: Annotated[str, Form()],
    obra_local: Annotated[str, Form()],
    tipo_obra: Annotated[str, Form()],
    responsavel: Annotated[str, Form()],
    observacoes_gerais: Annotated[str, Form()] = "",
    status: Annotated[str, Form()] = "Rascunho",
):
    usuario = exigir_login(request)
    if isinstance(usuario, RedirectResponse):
        return usuario
    with get_conn() as conn:
        anteprojeto_atual = get_anteprojeto_or_404(conn, anteprojeto_id)
        conn.execute(
            """
            UPDATE anteprojetos
            SET cliente = ?, obra_local = ?, tipo_obra = ?, responsavel = ?,
                observacoes_gerais = ?, status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (cliente, obra_local, tipo_obra, responsavel, observacoes_gerais, status, anteprojeto_id),
        )
        descricao = "Dados gerais atualizados"
        acao = "edicao"
        if anteprojeto_atual["status"] != status:
            acao = "status_alterado"
            descricao = f"Status alterado de {anteprojeto_atual['status']} para {status}"
        registrar_historico_anteprojeto(
            conn,
            anteprojeto_id,
            usuario,
            acao,
            descricao,
        )
        if anteprojeto_atual["status"] != status and status in STATUS_GERA_VERSAO:
            criar_versao_anteprojeto(conn, anteprojeto_id, usuario, STATUS_GERA_VERSAO[status])
    return RedirectResponse(f"/anteprojetos/{anteprojeto_id}", status_code=303)


@app.post("/anteprojetos/{anteprojeto_id}/itens")
async def salvar_item(request: Request, anteprojeto_id: int):
    usuario = exigir_login(request)
    if isinstance(usuario, RedirectResponse):
        return usuario
    form = await request.form()
    item_id = form.get("item_id")
    equipamento_id = int(form["equipamento_modelo_id"])

    with get_conn() as conn:
        anteprojeto = get_anteprojeto_or_404(conn, anteprojeto_id)
        equipamento = conn.execute(
            "SELECT * FROM equipamentos_modelo WHERE id = ?", (equipamento_id,)
        ).fetchone()
        if not equipamento:
            raise HTTPException(status_code=404, detail="Equipamento nao encontrado")

        schema = json.loads(equipamento["schema_json"])
        caminho_equipamento = equipamento_nome_exibicao(obter_caminho_equipamento(conn, equipamento_id))
        quantidade = int(form.get("quantidade") or 1)
        tipo_definicao = form.get("tipo_definicao") or "Engenharia dimensionar"
        situacao = form.get("situacao") or "Novo"
        if anteprojeto["tipo_obra"] == "Obra nova":
            situacao = "Novo"
        elif situacao not in SITUACAO_REFORMA_OPCOES:
            situacao = "Novo"
        if equipamento["nome"] == "Item 2 - Transportadores":
            campos = collect_transportador_campos(form)
        elif equipamento["nome"] == "Item 3 - Máquina de Limpeza Grain Cleaner EC":
            campos = collect_maquina_limpeza_campos(form)
        elif equipamento["nome"] == "Item 4 - Secadores Process Dryer":
            campos = collect_secador_campos(form)
        elif equipamento["nome"] == "Item 5 - Silo Pulmão Elevado":
            campos = collect_silo_pulmao_campos(form)
        else:
            campos = collect_campos(form, schema)
        campos_json = json.dumps(campos, ensure_ascii=False)
        observacao_inicial = (form.get("observacao_inicial") or "").strip()

        if item_id:
            item_atual = conn.execute(
                "SELECT retorno_engenharia FROM itens_anteprojeto WHERE id = ? AND anteprojeto_id = ?",
                (item_id, anteprojeto_id),
            ).fetchone()
            if not item_atual:
                raise HTTPException(status_code=404, detail="Item nao encontrado")
            conn.execute(
                """
                UPDATE itens_anteprojeto
                SET equipamento_modelo_id = ?, equipamento_nome = ?, quantidade = ?,
                    tipo_definicao = ?, situacao = ?, campos_json = ?,
                    observacao_inicial = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND anteprojeto_id = ?
                """,
                (
                    equipamento_id,
                    caminho_equipamento,
                    quantidade,
                    tipo_definicao,
                    situacao,
                    campos_json,
                    observacao_inicial,
                    item_id,
                    anteprojeto_id,
                ),
            )
            conn.execute(
                "INSERT INTO historico_item (item_id, descricao) VALUES (?, ?)",
                (item_id, "Item editado"),
            )
            salvar_opcoes_item(conn, int(item_id), equipamento_id, form)
            registrar_historico_anteprojeto(
                conn,
                anteprojeto_id,
                usuario,
                "edicao_item",
                f"Item editado: {caminho_equipamento}",
            )
        else:
            cur = conn.execute(
                """
                INSERT INTO itens_anteprojeto
                (anteprojeto_id, equipamento_modelo_id, equipamento_nome, quantidade,
                 tipo_definicao, situacao, campos_json, observacao_inicial, retorno_engenharia)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    anteprojeto_id,
                    equipamento_id,
                    caminho_equipamento,
                    quantidade,
                    tipo_definicao,
                    situacao,
                    campos_json,
                    observacao_inicial,
                    "",
                ),
            )
            conn.execute(
                "INSERT INTO historico_item (item_id, descricao) VALUES (?, ?)",
                (cur.lastrowid, "Item adicionado"),
            )
            salvar_opcoes_item(conn, cur.lastrowid, equipamento_id, form)
            registrar_historico_anteprojeto(
                conn,
                anteprojeto_id,
                usuario,
                "inclusao_item",
                f"Item incluido: {caminho_equipamento}",
            )
        touch_anteprojeto(conn, anteprojeto_id)

    return RedirectResponse(f"/anteprojetos/{anteprojeto_id}", status_code=303)


@app.post("/anteprojetos/{anteprojeto_id}/itens/{item_id}/retorno")
def salvar_retorno_engenharia(
    request: Request,
    anteprojeto_id: int,
    item_id: int,
    retorno_engenharia: Annotated[str, Form()] = "",
):
    usuario = exigir_login(request)
    if isinstance(usuario, RedirectResponse):
        return usuario
    with get_conn() as conn:
        get_anteprojeto_or_404(conn, anteprojeto_id)
        item = conn.execute(
            "SELECT id FROM itens_anteprojeto WHERE id = ? AND anteprojeto_id = ?",
            (item_id, anteprojeto_id),
        ).fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="Item nao encontrado")
        conn.execute(
            """
            UPDATE itens_anteprojeto
            SET retorno_engenharia = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND anteprojeto_id = ?
            """,
            (retorno_engenharia.strip(), item_id, anteprojeto_id),
        )
        conn.execute(
            "INSERT INTO historico_item (item_id, descricao) VALUES (?, ?)",
            (item_id, "Retorno da engenharia atualizado"),
        )
        registrar_historico_anteprojeto(
            conn,
            anteprojeto_id,
            usuario,
            "retorno_engenharia",
            "Retorno da engenharia alterado",
        )
        criar_versao_anteprojeto(conn, anteprojeto_id, usuario, "Retorno da engenharia")
        touch_anteprojeto(conn, anteprojeto_id)

    return RedirectResponse(f"/anteprojetos/{anteprojeto_id}", status_code=303)


@app.post("/anteprojetos/{anteprojeto_id}/itens/{item_id}/remover")
def remover_item(request: Request, anteprojeto_id: int, item_id: int):
    usuario = exigir_login(request)
    if isinstance(usuario, RedirectResponse):
        return usuario
    with get_conn() as conn:
        get_anteprojeto_or_404(conn, anteprojeto_id)
        item = conn.execute(
            "SELECT equipamento_nome FROM itens_anteprojeto WHERE id = ? AND anteprojeto_id = ?",
            (item_id, anteprojeto_id),
        ).fetchone()
        conn.execute(
            "DELETE FROM itens_anteprojeto WHERE id = ? AND anteprojeto_id = ?",
            (item_id, anteprojeto_id),
        )
        registrar_historico_anteprojeto(
            conn,
            anteprojeto_id,
            usuario,
            "exclusao_item",
            f"Item removido: {item['equipamento_nome'] if item else item_id}",
        )
        touch_anteprojeto(conn, anteprojeto_id)
    return RedirectResponse(f"/anteprojetos/{anteprojeto_id}", status_code=303)


@app.get("/anteprojetos/{anteprojeto_id}/pdf")
def pdf_anteprojeto(request: Request, anteprojeto_id: int):
    usuario = exigir_login(request)
    if isinstance(usuario, RedirectResponse):
        return usuario
    with get_conn() as conn:
        anteprojeto = get_anteprojeto_or_404(conn, anteprojeto_id)
        criar_versao_anteprojeto(conn, anteprojeto_id, usuario, "Geracao de PDF final")
        registrar_historico_anteprojeto(
            conn,
            anteprojeto_id,
            usuario,
            "pdf_final",
            "PDF final gerado",
        )
        itens = conn.execute(
            "SELECT * FROM itens_anteprojeto WHERE anteprojeto_id = ? ORDER BY tipo_definicao, equipamento_nome",
            (anteprojeto_id,),
        ).fetchall()
        itens = carregar_opcoes_itens(conn, [dict(item) for item in itens])
        buffer = gerar_pdf_anteprojeto(anteprojeto, itens)

    headers = {"Content-Disposition": f'inline; filename="anteprojeto-{anteprojeto_id}.pdf"'}
    return StreamingResponse(buffer, media_type="application/pdf", headers=headers)


@app.post("/anteprojetos/{anteprojeto_id}/versoes")
def criar_versao_manual(
    request: Request,
    anteprojeto_id: int,
    motivo: Annotated[str, Form()] = "Versao manual",
):
    usuario = exigir_login(request)
    if isinstance(usuario, RedirectResponse):
        return usuario
    motivo = (motivo or "").strip() or "Versao manual"
    with get_conn() as conn:
        get_anteprojeto_or_404(conn, anteprojeto_id)
        criar_versao_anteprojeto(conn, anteprojeto_id, usuario, motivo)
        registrar_historico_anteprojeto(
            conn,
            anteprojeto_id,
            usuario,
            "versao_manual",
            f"Nova versao criada: {motivo}",
        )
    return RedirectResponse(f"/anteprojetos/{anteprojeto_id}#versoes", status_code=303)


@app.get("/anteprojetos/{anteprojeto_id}/versoes/{versao_id}", response_class=HTMLResponse)
def visualizar_versao(request: Request, anteprojeto_id: int, versao_id: int):
    usuario = exigir_login(request)
    if isinstance(usuario, RedirectResponse):
        return usuario
    with get_conn() as conn:
        anteprojeto = get_anteprojeto_or_404(conn, anteprojeto_id)
        versao = conn.execute(
            """
            SELECT * FROM versoes_anteprojeto
            WHERE id = ? AND anteprojeto_id = ?
            """,
            (versao_id, anteprojeto_id),
        ).fetchone()
        if not versao:
            raise HTTPException(status_code=404, detail="Versao nao encontrada")

    snapshot = json.loads(versao["snapshot_json"])
    return templates.TemplateResponse(
        "versao_anteprojeto.html",
        {
            "request": request,
            "anteprojeto": anteprojeto,
            "versao": versao,
            "snapshot": snapshot,
            "snapshot_json_formatado": json.dumps(snapshot, ensure_ascii=False, indent=2),
        },
    )

