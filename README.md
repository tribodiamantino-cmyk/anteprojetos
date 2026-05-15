# Anteprojetos de Armazenagem Agricola

Sistema web para montar anteprojetos tecnicos de armazenagem agricola, selecionar equipamentos, registrar definicoes tecnicas, observacoes, retorno da engenharia, historico de alteracoes, versoes do anteprojeto e gerar relatorio para impressao/PDF.

## Estagio atual

O projeto esta em uso e evolucao continua. No momento, ele possui:

- Login com sessao e controle de usuarios.
- Perfil administrador para gerenciar usuarios e equipamentos.
- Cadastro e edicao de anteprojetos.
- Duplicacao e exclusao de anteprojetos.
- Catalogo de equipamentos padrao para o fluxo de anteprojeto:
  - Item 1 - Fluxo
  - Item 2 - Transportadores
  - Item 3 - Maquina de Limpeza Grain Cleaner EC
  - Item 4 - Secadores Process Dryer
  - Item 5 - Silo Pulmao Elevado
  - Item 6 - Silo Fundo Plano
  - Item 7 - Expedicao
- Opcoes configuraveis por equipamento, incluindo selecoes, campos numericos, texto e dependencias.
- Itens do anteprojeto com quantidade, situacao, definicao pela engenharia ou ja definida.
- Historico de alteracoes do anteprojeto e dos itens.
- Versoes/snapshots do anteprojeto.
- Relatorio final em layout compacto para impressao/salvar em PDF, com cards em duas colunas.
- Persistencia em SQLite local ou em caminho definido por variavel de ambiente.

## Regra de trabalho atual

Ate segunda ordem, sempre que fizermos atualizacoes no projeto, as alteracoes devem ser commitadas diretamente no Git e enviadas para o remoto `origin/main`, desde que a validacao basica passe e o repositorio esteja em estado consistente.

Fluxo esperado apos alteracoes:

```powershell
python -m compileall app
git status --short --branch
git add .
git commit -m "Mensagem objetiva da alteracao"
git push origin main
```

Tambem existe um arquivo `AGENTS.md` na raiz com instrucoes operacionais para o Codex/assistente ao abrir o projeto.

## Stack

- Python
- FastAPI
- Uvicorn
- SQLite
- Jinja2
- HTML/CSS/JavaScript simples
- Autenticacao com `passlib`, `bcrypt` e sessoes assinadas
- Relatorio de impressao/PDF via template HTML e `window.print()`
- ReportLab ainda esta listado como dependencia do projeto

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

## Acesso inicial

Na primeira inicializacao, caso ainda nao existam usuarios, o sistema cria um administrador padrao:

```text
Usuario: admin
Senha: admin123
```

Depois do primeiro acesso, recomenda-se alterar a senha ou criar outro usuario administrador.

## Banco de dados

Tabelas principais:

- `anteprojetos`
- `equipamentos_modelo`
- `equipamentos_atributos`
- `equipamentos_opcoes`
- `equipamentos_opcoes_valores`
- `equipamentos_opcoes_dependencias`
- `itens_anteprojeto`
- `itens_anteprojeto_opcoes`
- `historico_item`
- `historico_anteprojeto`
- `versoes_anteprojeto`
- `usuarios`

Na inicializacao, o sistema cria/migra as tabelas e garante os equipamentos padrao do fluxo atual.

O arquivo abaixo permanece disponivel para carga inicial opcional:

```text
app/data/equipamentos_seed.json
```

Para usar essa carga em uma base vazia:

```powershell
$env:SEED_EQUIPAMENTOS="1"
uvicorn app.main:app --reload
```

## Git e remoto

O repositorio esta configurado para trabalhar na branch `main` com remoto:

```text
origin https://github.com/tribodiamantino-cmyk/anteprojetos.git
```

Comandos uteis:

```powershell
git status --short --branch
git log -1 --oneline
git push origin main
```

O `.gitignore` ignora arquivos locais como:

- `.venv/`
- `__pycache__/`
- `*.pyc`
- `storage.db`
- `/data/*.db`
- `.env`

## Deploy no Railway

Arquivos incluidos:

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

Configure as variaveis de ambiente:

```text
DATABASE_PATH=/data/storage.db
SESSION_SECRET=uma-chave-grande-aleatoria
```

Com isso, o SQLite fica salvo no volume persistente e nao e perdido entre deploys.

## Estrutura

```text
app/
  main.py
  auth.py
  db.py
  pdf.py
  data/
    equipamentos_seed.json
  static/
    css/styles.css
    js/app.js
  templates/
Procfile
README.md
requirements.txt
runtime.txt
storage.db
```
