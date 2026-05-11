import json
from typing import Annotated

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .db import get_conn, init_db, touch_anteprojeto
from .pdf import gerar_pdf_anteprojeto


app = FastAPI(title="Anteprojetos de Armazenagem Agricola")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

STATUS_OPCOES = ["Rascunho", "Enviado para engenharia", "Retornado", "Revisado", "Finalizado"]
TIPO_OBRA_OPCOES = ["Obra nova", "Reforma"]
TIPO_DEFINICAO_OPCOES = ["Ja definido", "Parcialmente definido", "Engenharia dimensionar"]
SITUACAO_REFORMA_OPCOES = ["Novo", "Existente", "Substituir", "Adequar", "Remover"]
TIPOS_CAMPO_EQUIPAMENTO = ["text", "number", "select", "checkbox", "textarea", "info"]


@app.on_event("startup")
def startup():
    init_db()


def parse_json_row(row, column="schema_json"):
    data = dict(row)
    data["schema"] = json.loads(data[column])
    return data


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
    return item


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


def unique_name(conn, table, base_name):
    name = base_name
    suffix = 2
    while conn.execute(f"SELECT 1 FROM {table} WHERE nome = ?", (name,)).fetchone():
        name = f"{base_name} {suffix}"
        suffix += 1
    return name


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    with get_conn() as conn:
        anteprojetos = conn.execute(
            "SELECT * FROM anteprojetos ORDER BY updated_at DESC, id DESC"
        ).fetchall()
    return templates.TemplateResponse("index.html", {"request": request, "anteprojetos": anteprojetos})


@app.post("/anteprojetos/{anteprojeto_id}/duplicar")
def duplicar_anteprojeto(anteprojeto_id: int):
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
    return RedirectResponse(f"/anteprojetos/{novo_id}", status_code=303)


@app.post("/anteprojetos/{anteprojeto_id}/excluir")
def excluir_anteprojeto(anteprojeto_id: int):
    with get_conn() as conn:
        get_anteprojeto_or_404(conn, anteprojeto_id)
        conn.execute("DELETE FROM anteprojetos WHERE id = ?", (anteprojeto_id,))
    return RedirectResponse("/", status_code=303)


@app.get("/equipamentos", response_class=HTMLResponse)
def equipamentos_index(request: Request):
    with get_conn() as conn:
        equipamentos = conn.execute(
            "SELECT * FROM equipamentos_modelo ORDER BY ativo DESC, nome"
        ).fetchall()
    return templates.TemplateResponse(
        "equipamentos_index.html",
        {"request": request, "equipamentos": equipamentos},
    )


@app.get("/equipamentos/novo", response_class=HTMLResponse)
def novo_equipamento(request: Request):
    return templates.TemplateResponse(
        "equipamento_form.html",
        {
            "request": request,
            "equipamento": None,
            "schema": {"nome": "", "campos": []},
            "tipos_campo": TIPOS_CAMPO_EQUIPAMENTO,
        },
    )


@app.post("/equipamentos")
async def criar_equipamento(request: Request):
    form = await request.form()
    nome = (form.get("nome") or "").strip()
    if not nome:
        raise HTTPException(status_code=400, detail="Nome do equipamento e obrigatorio")

    schema = equipamento_from_form(form)
    ativo = 1 if form.get("ativo") == "1" else 0
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO equipamentos_modelo (nome, schema_json, ativo) VALUES (?, ?, ?)",
            (nome, json.dumps(schema, ensure_ascii=False), ativo),
        )
    return RedirectResponse(f"/equipamentos/{cur.lastrowid}/editar", status_code=303)


@app.get("/equipamentos/{equipamento_id}/editar", response_class=HTMLResponse)
def editar_equipamento(request: Request, equipamento_id: int):
    with get_conn() as conn:
        equipamento = conn.execute(
            "SELECT * FROM equipamentos_modelo WHERE id = ?", (equipamento_id,)
        ).fetchone()
        if not equipamento:
            raise HTTPException(status_code=404, detail="Equipamento nao encontrado")
    schema = normalize_equipamento_schema(equipamento["nome"], json.loads(equipamento["schema_json"]).get("campos", []))
    return templates.TemplateResponse(
        "equipamento_form.html",
        {
            "request": request,
            "equipamento": equipamento,
            "schema": schema,
            "tipos_campo": TIPOS_CAMPO_EQUIPAMENTO,
        },
    )


@app.post("/equipamentos/{equipamento_id}")
async def atualizar_equipamento(request: Request, equipamento_id: int):
    form = await request.form()
    nome = (form.get("nome") or "").strip()
    if not nome:
        raise HTTPException(status_code=400, detail="Nome do equipamento e obrigatorio")

    schema = equipamento_from_form(form)
    ativo = 1 if form.get("ativo") == "1" else 0
    with get_conn() as conn:
        equipamento = conn.execute(
            "SELECT id FROM equipamentos_modelo WHERE id = ?", (equipamento_id,)
        ).fetchone()
        if not equipamento:
            raise HTTPException(status_code=404, detail="Equipamento nao encontrado")
        conn.execute(
            "UPDATE equipamentos_modelo SET nome = ?, schema_json = ?, ativo = ? WHERE id = ?",
            (nome, json.dumps(schema, ensure_ascii=False), ativo, equipamento_id),
        )
    return RedirectResponse(f"/equipamentos/{equipamento_id}/editar", status_code=303)


@app.post("/equipamentos/{equipamento_id}/duplicar")
def duplicar_equipamento(equipamento_id: int):
    with get_conn() as conn:
        equipamento = conn.execute(
            "SELECT * FROM equipamentos_modelo WHERE id = ?", (equipamento_id,)
        ).fetchone()
        if not equipamento:
            raise HTTPException(status_code=404, detail="Equipamento nao encontrado")

        schema = json.loads(equipamento["schema_json"])
        novo_nome = unique_name(conn, "equipamentos_modelo", f"{equipamento['nome']} - Copia")
        schema["nome"] = novo_nome
        cur = conn.execute(
            "INSERT INTO equipamentos_modelo (nome, schema_json, ativo) VALUES (?, ?, ?)",
            (novo_nome, json.dumps(schema, ensure_ascii=False), equipamento["ativo"]),
        )
    return RedirectResponse(f"/equipamentos/{cur.lastrowid}/editar", status_code=303)


@app.post("/equipamentos/{equipamento_id}/inativar")
def inativar_equipamento(equipamento_id: int):
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
def excluir_equipamento(equipamento_id: int):
    with get_conn() as conn:
        equipamento = conn.execute(
            "SELECT id FROM equipamentos_modelo WHERE id = ?", (equipamento_id,)
        ).fetchone()
        if not equipamento:
            raise HTTPException(status_code=404, detail="Equipamento nao encontrado")

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
    cliente: Annotated[str, Form()],
    obra_local: Annotated[str, Form()],
    tipo_obra: Annotated[str, Form()],
    responsavel: Annotated[str, Form()],
    observacoes_gerais: Annotated[str, Form()] = "",
    status: Annotated[str, Form()] = "Rascunho",
):
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
    return RedirectResponse(f"/anteprojetos/{anteprojeto_id}", status_code=303)


@app.get("/anteprojetos/{anteprojeto_id}", response_class=HTMLResponse)
def editar_anteprojeto(
    request: Request,
    anteprojeto_id: int,
    item_id: int | None = None,
    retorno_item_id: int | None = None,
):
    with get_conn() as conn:
        anteprojeto = get_anteprojeto_or_404(conn, anteprojeto_id)
        equipamentos = [
            parse_json_row(row)
            for row in conn.execute(
                "SELECT * FROM equipamentos_modelo WHERE ativo = 1 ORDER BY nome"
            ).fetchall()
        ]
        itens_rows = conn.execute(
            """
            SELECT * FROM itens_anteprojeto
            WHERE anteprojeto_id = ?
            ORDER BY tipo_definicao, equipamento_nome, id
            """,
            (anteprojeto_id,),
        ).fetchall()
        itens = [parse_item(row) for row in itens_rows]
        itens_por_tipo = {tipo: [] for tipo in TIPO_DEFINICAO_OPCOES}
        for item in itens:
            itens_por_tipo.setdefault(item["tipo_definicao"], []).append(item)

        item_editando = None
        if item_id:
            item_editando = conn.execute(
                "SELECT * FROM itens_anteprojeto WHERE id = ? AND anteprojeto_id = ?",
                (item_id, anteprojeto_id),
            ).fetchone()
        retorno_item = None
        if retorno_item_id:
            retorno_item = conn.execute(
                "SELECT * FROM itens_anteprojeto WHERE id = ? AND anteprojeto_id = ?",
                (retorno_item_id, anteprojeto_id),
            ).fetchone()

    return templates.TemplateResponse(
        "anteprojeto_edit.html",
        {
            "request": request,
            "anteprojeto": anteprojeto,
            "equipamentos": equipamentos,
            "equipamentos_json": json.dumps([e["schema"] | {"id": e["id"]} for e in equipamentos], ensure_ascii=False),
            "itens": itens,
            "itens_por_tipo": itens_por_tipo,
            "item_editando": item_editando,
            "item_editando_campos": json.loads(item_editando["campos_json"]) if item_editando else {},
            "retorno_item": retorno_item,
            "status_opcoes": STATUS_OPCOES,
            "tipo_obra_opcoes": TIPO_OBRA_OPCOES,
            "tipo_definicao_opcoes": TIPO_DEFINICAO_OPCOES,
            "situacao_reforma_opcoes": SITUACAO_REFORMA_OPCOES,
        },
    )


@app.post("/anteprojetos/{anteprojeto_id}")
def atualizar_anteprojeto(
    anteprojeto_id: int,
    cliente: Annotated[str, Form()],
    obra_local: Annotated[str, Form()],
    tipo_obra: Annotated[str, Form()],
    responsavel: Annotated[str, Form()],
    observacoes_gerais: Annotated[str, Form()] = "",
    status: Annotated[str, Form()] = "Rascunho",
):
    with get_conn() as conn:
        get_anteprojeto_or_404(conn, anteprojeto_id)
        conn.execute(
            """
            UPDATE anteprojetos
            SET cliente = ?, obra_local = ?, tipo_obra = ?, responsavel = ?,
                observacoes_gerais = ?, status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (cliente, obra_local, tipo_obra, responsavel, observacoes_gerais, status, anteprojeto_id),
        )
    return RedirectResponse(f"/anteprojetos/{anteprojeto_id}", status_code=303)


@app.post("/anteprojetos/{anteprojeto_id}/itens")
async def salvar_item(request: Request, anteprojeto_id: int):
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
        quantidade = int(form.get("quantidade") or 1)
        tipo_definicao = form.get("tipo_definicao") or "Engenharia dimensionar"
        situacao = form.get("situacao") or "Novo"
        if anteprojeto["tipo_obra"] == "Obra nova":
            situacao = "Novo"
        elif situacao not in SITUACAO_REFORMA_OPCOES:
            situacao = "Novo"
        campos_json = json.dumps(collect_campos(form, schema), ensure_ascii=False)
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
                    equipamento["nome"],
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
                    equipamento["nome"],
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
        touch_anteprojeto(conn, anteprojeto_id)

    return RedirectResponse(f"/anteprojetos/{anteprojeto_id}", status_code=303)


@app.post("/anteprojetos/{anteprojeto_id}/itens/{item_id}/retorno")
def salvar_retorno_engenharia(
    anteprojeto_id: int,
    item_id: int,
    retorno_engenharia: Annotated[str, Form()] = "",
):
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
        touch_anteprojeto(conn, anteprojeto_id)

    return RedirectResponse(f"/anteprojetos/{anteprojeto_id}", status_code=303)


@app.post("/anteprojetos/{anteprojeto_id}/itens/{item_id}/remover")
def remover_item(anteprojeto_id: int, item_id: int):
    with get_conn() as conn:
        get_anteprojeto_or_404(conn, anteprojeto_id)
        conn.execute(
            "DELETE FROM itens_anteprojeto WHERE id = ? AND anteprojeto_id = ?",
            (item_id, anteprojeto_id),
        )
        touch_anteprojeto(conn, anteprojeto_id)
    return RedirectResponse(f"/anteprojetos/{anteprojeto_id}", status_code=303)


@app.get("/anteprojetos/{anteprojeto_id}/pdf")
def pdf_anteprojeto(anteprojeto_id: int):
    with get_conn() as conn:
        anteprojeto = get_anteprojeto_or_404(conn, anteprojeto_id)
        itens = conn.execute(
            "SELECT * FROM itens_anteprojeto WHERE anteprojeto_id = ? ORDER BY tipo_definicao, equipamento_nome",
            (anteprojeto_id,),
        ).fetchall()
        buffer = gerar_pdf_anteprojeto(anteprojeto, itens)

    headers = {"Content-Disposition": f'inline; filename="anteprojeto-{anteprojeto_id}.pdf"'}
    return StreamingResponse(buffer, media_type="application/pdf", headers=headers)
