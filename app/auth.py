from fastapi import Request
from fastapi.responses import RedirectResponse
from passlib.context import CryptContext

from .db import get_conn


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_senha(senha):
    return pwd_context.hash(senha)


def verificar_senha(senha, senha_hash):
    return pwd_context.verify(senha, senha_hash)


def get_usuario_logado(request: Request):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return None
    return {
        "id": usuario_id,
        "nome": request.session.get("usuario_nome"),
        "usuario": request.session.get("usuario"),
        "is_admin": request.session.get("is_admin", 0),
    }


def exigir_login(request: Request):
    usuario = get_usuario_logado(request)
    if not usuario:
        return RedirectResponse("/login", status_code=303)
    return usuario


def exigir_admin(request: Request):
    usuario = exigir_login(request)
    if isinstance(usuario, RedirectResponse):
        return usuario
    if not usuario.get("is_admin"):
        return RedirectResponse("/", status_code=303)
    return usuario


def autenticar_usuario(usuario, senha):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM usuarios WHERE usuario = ? AND ativo = 1",
            (usuario,),
        ).fetchone()
    if not row or not verificar_senha(senha, row["senha_hash"]):
        return None
    return row
