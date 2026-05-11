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
                schema_json TEXT NOT NULL,
                ativo INTEGER NOT NULL DEFAULT 1
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
            """
        )
        seed_equipamentos(conn)
        seed_admin(conn)


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
