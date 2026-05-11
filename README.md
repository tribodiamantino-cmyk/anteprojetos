# Anteprojetos de Armazenagem Agricola

Sistema web para montar anteprojetos tecnicos de armazenagem agricola, selecionar equipamentos, registrar especificacoes, observacoes, retorno da engenharia e gerar PDF.

## Stack

- Python FastAPI
- SQLite
- Jinja2
- HTML/CSS/JS simples
- PDF com ReportLab

## Rodar localmente no Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Acesse:

```text
http://127.0.0.1:8000
```

Por padrao, o banco SQLite local sera criado em:

```text
storage.db
```

Tambem e possivel definir outro caminho:

```powershell
$env:DATABASE_PATH="C:\caminho\para\storage.db"
uvicorn app.main:app --reload
```

Se a pasta do banco nao existir, o sistema cria automaticamente.

## Banco de dados

Tabelas principais:

- `anteprojetos`
- `equipamentos_modelo`
- `itens_anteprojeto`
- `historico_item`

Na primeira execucao, o sistema cria as tabelas e carrega os equipamentos iniciais a partir de:

```text
app/data/equipamentos_seed.json
```

Depois da primeira carga, os equipamentos passam a ser mantidos no banco SQLite pela tela `Equipamentos`.

## Comandos Git

```powershell
git init
git add .
git commit -m "Versao inicial do sistema de anteprojetos"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
git push -u origin main
```

O `.gitignore` ignora arquivos locais como:

- `.venv/`
- `__pycache__/`
- `*.pyc`
- `storage.db`
- `/data/*.db`
- `.env`

## Deploy no Railway

Arquivos ja incluidos:

- `Procfile`
- `runtime.txt`

Start command:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Configure um volume persistente no Railway:

```text
Mount path: /data
```

Configure a variavel de ambiente:

```text
DATABASE_PATH=/data/storage.db
```

Com isso, o SQLite fica salvo no volume persistente e nao e perdido entre deploys.

## Estrutura

```text
app/
  main.py
  db.py
  pdf.py
  data/
    equipamentos_seed.json
  static/
    css/styles.css
    js/app.js
  templates/
requirements.txt
Procfile
runtime.txt
README.md
```
