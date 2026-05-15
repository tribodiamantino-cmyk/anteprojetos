# Instrucoes do projeto para Codex

Estas instrucoes valem para todo o repositorio.

## Contexto

Este e um sistema FastAPI para anteprojetos de armazenagem agricola. O projeto usa SQLite, Jinja2, HTML/CSS/JavaScript simples e templates server-side.

## Fluxo de trabalho atual

- Ate segunda ordem, sempre que forem feitas atualizacoes no projeto, criar commit diretamente e enviar para `origin/main`.
- Antes do commit, executar validacao basica quando a mudanca permitir:

```powershell
python -m compileall app
```

- Conferir o estado do Git antes e depois:

```powershell
git status --short --branch
```

- Usar mensagens de commit objetivas em portugues.
- Nao reverter alteracoes do usuario sem pedido explicito.
- Manter as mudancas focadas no pedido atual.

## Padroes tecnicos

- Preferir alteracoes simples e compativeis com a estrutura atual.
- Manter CSS, templates e rotas no estilo ja existente.
- Evitar dependencias novas sem necessidade clara.
- Para relatorios de impressao/PDF, preservar layout compacto e aproveitamento de pagina A4.
