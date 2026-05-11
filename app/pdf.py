import json
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


TIPOS_DEFINICAO = [
    "Ja definido",
    "Parcialmente definido",
    "Engenharia dimensionar",
]


def _p(text, style):
    text = "" if text is None else str(text)
    safe = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )
    return Paragraph(safe, style)


def _format_campos(campos_json):
    campos = json.loads(campos_json or "{}")
    linhas = []
    for nome, valor in campos.items():
        if isinstance(valor, list):
            valor = ", ".join(valor)
        if valor not in ("", None, []):
            linhas.append(f"<b>{nome}:</b> {valor}")
    return "<br/>".join(linhas) if linhas else "Sem especificacoes preenchidas."


def _format_opcoes(opcoes):
    linhas = []
    for opcao in opcoes or []:
        valor = opcao.get("valor_rotulo") or opcao.get("valor") or ""
        if valor:
            linhas.append(f"<b>{opcao['opcao_nome']}:</b> {valor}")
    return "<br/>".join(linhas)


def gerar_pdf_anteprojeto(anteprojeto, itens):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.3 * cm,
        bottomMargin=1.3 * cm,
        title=f"Anteprojeto {anteprojeto['id']}",
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=8, leading=10))
    styles.add(ParagraphStyle(name="ItemTitle", parent=styles["BodyText"], fontSize=10, leading=12, spaceAfter=3))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], fontSize=13, leading=16, spaceBefore=10))

    story = [
        _p(f"Anteprojeto tecnico #{anteprojeto['id']}", styles["Title"]),
        Spacer(1, 8),
    ]

    dados = [
        ["Cliente", anteprojeto["cliente"]],
        ["Obra/local", anteprojeto["obra_local"]],
        ["Tipo da obra", anteprojeto["tipo_obra"]],
        ["Responsavel", anteprojeto["responsavel"]],
        ["Status", anteprojeto["status"]],
    ]
    tabela = Table([[ _p(a, styles["Small"]), _p(b, styles["Small"]) ] for a, b in dados], colWidths=[4 * cm, 13 * cm])
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef2f6")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9d2dc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [tabela, Spacer(1, 10)]

    por_tipo = {tipo: [] for tipo in TIPOS_DEFINICAO}
    for item in itens:
        por_tipo.setdefault(item["tipo_definicao"], []).append(item)

    titulos = {
        "Ja definido": "Itens ja definidos",
        "Parcialmente definido": "Itens parcialmente definidos",
        "Engenharia dimensionar": "Itens para dimensionamento da engenharia",
    }

    for tipo in TIPOS_DEFINICAO:
        story.append(_p(titulos[tipo], styles["Section"]))
        grupo = por_tipo.get(tipo, [])
        if not grupo:
            story.append(_p("Nenhum item neste grupo.", styles["BodyText"]))
            continue

        for item in grupo:
            titulo = f"{item['quantidade']} un. - {item['equipamento_nome']} - {item['situacao']}"
            detalhes = [_format_campos(item["campos_json"])]
            opcoes = _format_opcoes(item.get("opcoes"))
            if opcoes:
                detalhes.append(f"<b>Acessorios e opcionais:</b><br/>{opcoes}")
            if item["observacao_inicial"]:
                detalhes.append(f"<b>Observacao inicial:</b> {item['observacao_inicial']}")
            if item["retorno_engenharia"]:
                detalhes.append(f"<b>Retorno da engenharia:</b> {item['retorno_engenharia']}")

            item_table = Table(
                [
                    [_p(f"<b>{titulo}</b>", styles["ItemTitle"])],
                    [_p("<br/>".join(detalhes), styles["BodyText"])],
                ],
                colWidths=[17 * cm],
            )
            item_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f4f7f9")),
                ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9d2dc")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d9e0e8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(item_table)
            story.append(Spacer(1, 8))

    story.append(_p("Observacoes gerais", styles["Section"]))
    story.append(_p(anteprojeto["observacoes_gerais"] or "Sem observacoes gerais.", styles["BodyText"]))

    doc.build(story)
    buffer.seek(0)
    return buffer
