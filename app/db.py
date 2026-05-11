import json
import os
import sqlite3
from pathlib import Path

from passlib.context import CryptContext


BASE_DIR = Path(__file__).resolve().parent.parent
SEED_PATH = Path(__file__).resolve().parent / "data" / "equipamentos_seed.json"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_db_path():
    configured_path = os.getenv("DATABASE_PATH")
    if configured_path:
        return Path(configured_path)
    return BASE_DIR / "storage.db"


def get_conn():
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS anteprojetos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente TEXT NOT NULL,
                obra_local TEXT NOT NULL,
                tipo_obra TEXT NOT NULL CHECK (tipo_obra IN ('Obra nova', 'Reforma')),
                responsavel TEXT NOT NULL,
                observacoes_gerais TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS equipamentos_modelo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id INTEGER,
                nome TEXT NOT NULL,
                descricao TEXT,
                categoria TEXT,
                subcategoria TEXT,
                fabricante TEXT,
                modelo TEXT,
                schema_json TEXT NOT NULL,
                ativo INTEGER NOT NULL DEFAULT 1,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES equipamentos_modelo(id) ON DELETE RESTRICT
            );

            CREATE TABLE IF NOT EXISTS equipamentos_atributos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipamento_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                chave TEXT NOT NULL,
                tipo TEXT NOT NULL CHECK (tipo IN ('texto', 'numero', 'inteiro', 'booleano', 'lista', 'json')),
                valor TEXT,
                unidade TEXT,
                ordem INTEGER DEFAULT 0,
                obrigatorio INTEGER DEFAULT 0,
                visivel_resumo INTEGER DEFAULT 1,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (equipamento_id) REFERENCES equipamentos_modelo(id) ON DELETE CASCADE,
                UNIQUE (equipamento_id, chave)
            );

            CREATE TABLE IF NOT EXISTS itens_anteprojeto (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                anteprojeto_id INTEGER NOT NULL,
                equipamento_modelo_id INTEGER NOT NULL,
                equipamento_nome TEXT NOT NULL,
                quantidade INTEGER NOT NULL DEFAULT 1,
                tipo_definicao TEXT NOT NULL,
                situacao TEXT NOT NULL,
                campos_json TEXT NOT NULL,
                observacao_inicial TEXT,
                retorno_engenharia TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (anteprojeto_id) REFERENCES anteprojetos(id) ON DELETE CASCADE,
                FOREIGN KEY (equipamento_modelo_id) REFERENCES equipamentos_modelo(id)
            );

            CREATE TABLE IF NOT EXISTS equipamentos_opcoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipamento_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                chave TEXT NOT NULL,
                tipo TEXT NOT NULL CHECK (tipo IN ('booleano', 'selecao', 'texto', 'numero')),
                obrigatorio INTEGER DEFAULT 0,
                ordem INTEGER DEFAULT 0,
                ativo INTEGER DEFAULT 1,
                FOREIGN KEY (equipamento_id) REFERENCES equipamentos_modelo(id) ON DELETE CASCADE,
                UNIQUE (equipamento_id, chave)
            );

            CREATE TABLE IF NOT EXISTS equipamentos_opcoes_valores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                opcao_id INTEGER NOT NULL,
                valor TEXT NOT NULL,
                rotulo TEXT NOT NULL,
                ordem INTEGER DEFAULT 0,
                ativo INTEGER DEFAULT 1,
                FOREIGN KEY (opcao_id) REFERENCES equipamentos_opcoes(id) ON DELETE CASCADE,
                UNIQUE (opcao_id, valor)
            );

            CREATE TABLE IF NOT EXISTS itens_anteprojeto_opcoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_anteprojeto_id INTEGER NOT NULL,
                opcao_id INTEGER NOT NULL,
                opcao_nome TEXT NOT NULL,
                opcao_chave TEXT NOT NULL,
                valor TEXT,
                valor_rotulo TEXT,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (item_anteprojeto_id) REFERENCES itens_anteprojeto(id) ON DELETE CASCADE,
                FOREIGN KEY (opcao_id) REFERENCES equipamentos_opcoes(id)
            );

            CREATE TABLE IF NOT EXISTS historico_item (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                descricao TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (item_id) REFERENCES itens_anteprojeto(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                usuario TEXT UNIQUE NOT NULL,
                senha_hash TEXT NOT NULL,
                is_admin INTEGER NOT NULL DEFAULT 0,
                ativo INTEGER NOT NULL DEFAULT 1,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS historico_anteprojeto (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                anteprojeto_id INTEGER NOT NULL,
                usuario_id INTEGER,
                usuario_nome TEXT,
                acao TEXT NOT NULL,
                descricao TEXT,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (anteprojeto_id) REFERENCES anteprojetos(id) ON DELETE CASCADE,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
            );

            CREATE TABLE IF NOT EXISTS versoes_anteprojeto (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                anteprojeto_id INTEGER NOT NULL,
                numero_versao INTEGER NOT NULL,
                usuario_id INTEGER,
                usuario_nome TEXT,
                motivo TEXT NOT NULL,
                snapshot_json TEXT NOT NULL,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (anteprojeto_id) REFERENCES anteprojetos(id) ON DELETE CASCADE,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
                UNIQUE (anteprojeto_id, numero_versao)
            );
            """
        )
        migrate_equipamentos(conn)
        seed_equipamentos(conn)
        seed_silo_fundo_plano_evo50_exemplo(conn)
        seed_admin(conn)


def column_exists(conn, table, column):
    columns = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row["name"] == column for row in columns)


def migrate_equipamentos(conn):
    migrate_equipamentos_modelo_unique_nome(conn)
    columns = {
        "parent_id": "INTEGER",
        "descricao": "TEXT",
        "categoria": "TEXT",
        "subcategoria": "TEXT",
        "fabricante": "TEXT",
        "modelo": "TEXT",
        "criado_em": "TEXT",
        "atualizado_em": "TEXT",
    }
    for column, definition in columns.items():
        if not column_exists(conn, "equipamentos_modelo", column):
            conn.execute(f"ALTER TABLE equipamentos_modelo ADD COLUMN {column} {definition}")
    conn.execute(
        """
        UPDATE equipamentos_modelo
        SET criado_em = COALESCE(criado_em, CURRENT_TIMESTAMP),
            atualizado_em = COALESCE(atualizado_em, CURRENT_TIMESTAMP)
        """
    )

    migrate_schema_json_to_atributos(conn)


def migrate_equipamentos_modelo_unique_nome(conn):
    indexes = conn.execute("PRAGMA index_list(equipamentos_modelo)").fetchall()
    has_unique_nome = False
    for index in indexes:
        if not index["unique"]:
            continue
        columns = conn.execute(f"PRAGMA index_info({index['name']})").fetchall()
        if [column["name"] for column in columns] == ["nome"]:
            has_unique_nome = True
            break
    if not has_unique_nome:
        return

    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS equipamentos_modelo_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_id INTEGER,
            nome TEXT NOT NULL,
            descricao TEXT,
            categoria TEXT,
            subcategoria TEXT,
            fabricante TEXT,
            modelo TEXT,
            schema_json TEXT NOT NULL,
            ativo INTEGER NOT NULL DEFAULT 1,
            criado_em TEXT,
            atualizado_em TEXT,
            FOREIGN KEY (parent_id) REFERENCES equipamentos_modelo_new(id) ON DELETE RESTRICT
        )
        """
    )
    conn.execute(
        """
        INSERT INTO equipamentos_modelo_new
        (id, parent_id, nome, descricao, categoria, subcategoria, fabricante, modelo,
         schema_json, ativo, criado_em, atualizado_em)
        SELECT id, parent_id, nome, descricao, categoria, subcategoria, fabricante, modelo,
               schema_json, ativo, criado_em, atualizado_em
        FROM equipamentos_modelo
        """
    )
    conn.execute("DROP TABLE equipamentos_modelo")
    conn.execute("ALTER TABLE equipamentos_modelo_new RENAME TO equipamentos_modelo")
    conn.execute("PRAGMA foreign_keys = ON")


def normalize_chave(value):
    normalized = (value or "").strip().lower()
    replacements = {
        "á": "a",
        "à": "a",
        "ã": "a",
        "â": "a",
        "ä": "a",
        "é": "e",
        "è": "e",
        "ê": "e",
        "ë": "e",
        "í": "i",
        "ì": "i",
        "î": "i",
        "ï": "i",
        "ó": "o",
        "ò": "o",
        "õ": "o",
        "ô": "o",
        "ö": "o",
        "ú": "u",
        "ù": "u",
        "û": "u",
        "ü": "u",
        "ç": "c",
    }
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    chars = [char if char.isalnum() else "_" for char in normalized]
    slug = "_".join(filter(None, "".join(chars).split("_")))
    return slug or "atributo"


def migrate_schema_json_to_atributos(conn):
    equipamentos = conn.execute("SELECT id, schema_json FROM equipamentos_modelo").fetchall()
    for equipamento in equipamentos:
        total = conn.execute(
            "SELECT COUNT(*) FROM equipamentos_atributos WHERE equipamento_id = ?",
            (equipamento["id"],),
        ).fetchone()[0]
        if total:
            continue

        try:
            schema = json.loads(equipamento["schema_json"] or "{}")
        except json.JSONDecodeError:
            schema = {}

        campos = schema.get("campos") or []
        for index, campo in enumerate(campos, start=1):
            nome = (campo.get("nome") or "").strip()
            if not nome:
                continue
            tipo = {
                "text": "texto",
                "textarea": "texto",
                "number": "numero",
                "select": "lista",
                "checkbox": "lista",
                "info": "texto",
            }.get(campo.get("tipo"), "texto")
            valor = ""
            if campo.get("tipo") in ("select", "checkbox"):
                valor = "\n".join(campo.get("opcoes") or [])
            elif campo.get("tipo") == "info":
                valor = campo.get("texto") or ""
            conn.execute(
                """
                INSERT OR IGNORE INTO equipamentos_atributos
                (equipamento_id, nome, chave, tipo, valor, ordem, obrigatorio, visivel_resumo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    equipamento["id"],
                    nome,
                    normalize_chave(nome),
                    tipo,
                    valor,
                    int(campo.get("ordem") or index),
                    1 if campo.get("obrigatorio") else 0,
                    1,
                ),
            )


def seed_equipamentos(conn):
    if os.getenv("SEED_EQUIPAMENTOS", "0") != "1":
        return

    total = conn.execute("SELECT COUNT(*) FROM equipamentos_modelo").fetchone()[0]
    if total:
        return

    equipamentos = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    for equipamento in equipamentos:
        conn.execute(
            "INSERT INTO equipamentos_modelo (nome, schema_json) VALUES (?, ?)",
            (equipamento["nome"], json.dumps(equipamento, ensure_ascii=False)),
        )
    migrate_schema_json_to_atributos(conn)


def insert_equipamento_seed(
    conn,
    nome,
    parent_id=None,
    categoria="",
    subcategoria="",
    fabricante="",
    modelo="",
):
    cur = conn.execute(
        """
        INSERT INTO equipamentos_modelo
        (parent_id, nome, descricao, categoria, subcategoria, fabricante, modelo, schema_json, ativo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            parent_id,
            nome,
            "",
            categoria,
            subcategoria,
            fabricante,
            modelo,
            json.dumps({"nome": nome, "campos": []}, ensure_ascii=False),
            1,
        ),
    )
    return cur.lastrowid


def insert_atributo_seed(conn, equipamento_id, nome, chave, tipo, valor="", unidade="", ordem=0):
    conn.execute(
        """
        INSERT OR IGNORE INTO equipamentos_atributos
        (equipamento_id, nome, chave, tipo, valor, unidade, ordem, obrigatorio, visivel_resumo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (equipamento_id, nome, chave, tipo, valor, unidade, ordem, 0, 1),
    )


def seed_silo_fundo_plano_evo50_exemplo(conn):
    existente = conn.execute(
        "SELECT id FROM equipamentos_modelo WHERE parent_id IS NULL AND nome = ?",
        ("Silo Fundo Plano EVO 50",),
    ).fetchone()
    if existente:
        seed_opcoes_silo_evo50(conn, existente["id"])
        return

    silo_id = insert_equipamento_seed(
        conn,
        "Silo Fundo Plano EVO 50",
        categoria="Silo",
        subcategoria="Fundo Plano",
        fabricante="GSI",
        modelo="EVO 50",
    )
    insert_atributo_seed(conn, silo_id, "Linha", "linha", "texto", "EVO 50", "", 1)
    insert_atributo_seed(conn, silo_id, "Tipo de silo", "tipo_silo", "texto", "Fundo Plano", "", 2)
    seed_opcoes_silo_evo50(conn, silo_id)

    for diametro_ordem, diametro_pes in enumerate((18, 21, 24), start=1):
        diametro_id = insert_equipamento_seed(conn, f"Diametro {diametro_pes}'", parent_id=silo_id)
        insert_atributo_seed(
            conn,
            diametro_id,
            "Diametro em pes",
            "diametro_pes",
            "numero",
            str(diametro_pes),
            "pes",
            1,
        )
        insert_atributo_seed(conn, diametro_id, "Diametro em metros", "diametro_m", "numero", "", "m", 2)

        for aneis in range(6, 13):
            aneis_id = insert_equipamento_seed(conn, f"{aneis} aneis", parent_id=diametro_id)
            insert_atributo_seed(conn, aneis_id, "Aneis", "aneis", "inteiro", str(aneis), "", 1)
            insert_atributo_seed(conn, aneis_id, "Capacidade m3", "capacidade_m3", "numero", "", "m3", 2)
            insert_atributo_seed(conn, aneis_id, "Capacidade t", "capacidade_t", "numero", "", "t", 3)
            insert_atributo_seed(conn, aneis_id, "Sacas", "sacas", "numero", "", "sc", 4)
            insert_atributo_seed(conn, aneis_id, "Altura corpo", "altura_corpo_m", "numero", "", "m", 5)
            insert_atributo_seed(conn, aneis_id, "Altura total", "altura_total_m", "numero", "", "m", 6)


def insert_opcao_seed(conn, equipamento_id, nome, chave, tipo, valores=None, ordem=0, obrigatorio=0):
    cur = conn.execute(
        """
        INSERT OR IGNORE INTO equipamentos_opcoes
        (equipamento_id, nome, chave, tipo, obrigatorio, ordem, ativo)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (equipamento_id, nome, chave, tipo, obrigatorio, ordem, 1),
    )
    opcao = conn.execute(
        "SELECT id FROM equipamentos_opcoes WHERE equipamento_id = ? AND chave = ?",
        (equipamento_id, chave),
    ).fetchone()
    opcao_id = opcao["id"] if opcao else cur.lastrowid

    for index, valor in enumerate(valores or [], start=1):
        conn.execute(
            """
            INSERT OR IGNORE INTO equipamentos_opcoes_valores
            (opcao_id, valor, rotulo, ordem, ativo)
            VALUES (?, ?, ?, ?, ?)
            """,
            (opcao_id, valor[0], valor[1], index, 1),
        )


def seed_opcoes_silo_evo50(conn, silo_id):
    insert_opcao_seed(
        conn,
        silo_id,
        "Escada",
        "escada",
        "selecao",
        [("marinheiro", "Marinheiro"), ("caracol", "Caracol")],
        1,
    )
    insert_opcao_seed(
        conn,
        silo_id,
        "Termometria",
        "termometria",
        "selecao",
        [("nenhuma", "Nenhuma"), ("analogica", "Analogica"), ("digital", "Digital")],
        2,
    )
    insert_opcao_seed(
        conn,
        silo_id,
        "Rosca varredora",
        "rosca_varredora",
        "selecao",
        [
            ("nenhuma", "Nenhuma"),
            ("standard", "Standard"),
            ("semiautomatica", "Semiautomatica"),
            ("automatica", "Automatica"),
        ],
        3,
    )
    insert_opcao_seed(conn, silo_id, "Sensor de nivel", "sensor_nivel", "booleano", ordem=4)
    insert_opcao_seed(conn, silo_id, "Porta intermediaria", "porta_intermediaria", "booleano", ordem=5)
    insert_opcao_seed(conn, silo_id, "Descarga lateral", "descarga_lateral", "booleano", ordem=6)
    insert_opcao_seed(conn, silo_id, "Aeracao", "aeracao", "booleano", ordem=7)
    insert_opcao_seed(
        conn,
        silo_id,
        "Espalhador",
        "espalhador",
        "selecao",
        [("nenhum", "Nenhum"), ("eg", "EG"), ("5000", "5000"), ("10000", "10000")],
        8,
    )


def obter_caminho_equipamento(conn, equipamento_id):
    partes = []
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
        partes.append(row["nome"])
        atual_id = row["parent_id"]

    return " > ".join(reversed(partes))


def obter_opcoes_disponiveis(conn, equipamento_id):
    cadeia_ids = []
    visitados = set()
    atual_id = equipamento_id

    while atual_id and atual_id not in visitados:
        visitados.add(atual_id)
        row = conn.execute(
            "SELECT id, parent_id FROM equipamentos_modelo WHERE id = ?",
            (atual_id,),
        ).fetchone()
        if not row:
            break
        cadeia_ids.append(row["id"])
        atual_id = row["parent_id"]

    opcoes_por_chave = {}
    for source_id in reversed(cadeia_ids):
        opcoes = conn.execute(
            """
            SELECT * FROM equipamentos_opcoes
            WHERE equipamento_id = ? AND ativo = 1
            ORDER BY ordem, nome, id
            """,
            (source_id,),
        ).fetchall()
        for opcao in opcoes:
            valores = conn.execute(
                """
                SELECT valor, rotulo
                FROM equipamentos_opcoes_valores
                WHERE opcao_id = ? AND ativo = 1
                ORDER BY ordem, rotulo, id
                """,
                (opcao["id"],),
            ).fetchall()
            data = dict(opcao)
            data["valores"] = [dict(valor) for valor in valores]
            opcoes_por_chave[opcao["chave"]] = data

    return sorted(opcoes_por_chave.values(), key=lambda item: (item["ordem"], item["nome"], item["id"]))


def touch_anteprojeto(conn, anteprojeto_id):
    conn.execute(
        "UPDATE anteprojetos SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (anteprojeto_id,),
    )


def seed_admin(conn):
    total = conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
    if total:
        return
    conn.execute(
        """
        INSERT INTO usuarios (nome, usuario, senha_hash, is_admin, ativo)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("Administrador", "admin", pwd_context.hash("admin123"), 1, 1),
    )


def registrar_historico_anteprojeto(conn, anteprojeto_id, usuario, acao, descricao=None):
    conn.execute(
        """
        INSERT INTO historico_anteprojeto
        (anteprojeto_id, usuario_id, usuario_nome, acao, descricao)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            anteprojeto_id,
            usuario.get("id") if usuario else None,
            usuario.get("nome") if usuario else None,
            acao,
            descricao,
        ),
    )


def row_to_dict(row):
    return dict(row) if row else None


def gerar_snapshot_anteprojeto(conn, anteprojeto_id):
    anteprojeto = conn.execute(
        "SELECT * FROM anteprojetos WHERE id = ?",
        (anteprojeto_id,),
    ).fetchone()
    if not anteprojeto:
        return None

    itens = []
    equipamento_ids = set()
    itens_rows = conn.execute(
        """
        SELECT * FROM itens_anteprojeto
        WHERE anteprojeto_id = ?
        ORDER BY tipo_definicao, equipamento_nome, id
        """,
        (anteprojeto_id,),
    ).fetchall()
    for row in itens_rows:
        item = row_to_dict(row)
        item["campos"] = json.loads(item.pop("campos_json") or "{}")
        opcoes_rows = conn.execute(
            """
            SELECT opcao_id, opcao_nome, opcao_chave, valor, valor_rotulo
            FROM itens_anteprojeto_opcoes
            WHERE item_anteprojeto_id = ?
            ORDER BY id
            """,
            (item["id"],),
        ).fetchall()
        item["opcoes"] = [dict(opcao) for opcao in opcoes_rows]
        equipamento_ids.add(item["equipamento_modelo_id"])
        itens.append(item)

    equipamentos = []
    if equipamento_ids:
        placeholders = ",".join("?" for _ in equipamento_ids)
        equipamentos_rows = conn.execute(
            f"""
            SELECT * FROM equipamentos_modelo
            WHERE id IN ({placeholders})
            ORDER BY nome
            """,
            tuple(equipamento_ids),
        ).fetchall()
        for row in equipamentos_rows:
            equipamento = row_to_dict(row)
            equipamento["schema"] = json.loads(equipamento.pop("schema_json") or "{}")
            equipamentos.append(equipamento)

    return {
        "anteprojeto": row_to_dict(anteprojeto),
        "itens": itens,
        "equipamentos": equipamentos,
    }


def criar_versao_anteprojeto(conn, anteprojeto_id, usuario, motivo):
    snapshot = gerar_snapshot_anteprojeto(conn, anteprojeto_id)
    if not snapshot:
        return None

    numero_versao = conn.execute(
        """
        SELECT COALESCE(MAX(numero_versao), 0) + 1
        FROM versoes_anteprojeto
        WHERE anteprojeto_id = ?
        """,
        (anteprojeto_id,),
    ).fetchone()[0]
    cur = conn.execute(
        """
        INSERT INTO versoes_anteprojeto
        (anteprojeto_id, numero_versao, usuario_id, usuario_nome, motivo, snapshot_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            anteprojeto_id,
            numero_versao,
            usuario.get("id") if usuario else None,
            usuario.get("nome") if usuario else None,
            motivo,
            json.dumps(snapshot, ensure_ascii=False, indent=2),
        ),
    )
    return cur.lastrowid
