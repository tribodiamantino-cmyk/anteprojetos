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
                nome TEXT NOT NULL UNIQUE,
                descricao TEXT,
                categoria TEXT,
                subcategoria TEXT,
                fabricante TEXT,
                modelo TEXT,
                schema_json TEXT NOT NULL,
                ativo INTEGER NOT NULL DEFAULT 1,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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
        seed_admin(conn)


def column_exists(conn, table, column):
    columns = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row["name"] == column for row in columns)


def migrate_equipamentos(conn):
    columns = {
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
