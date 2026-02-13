import os
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def salvar_relatorio_pdf(conteudo: str, nome_base: str = "relatorio", pasta: str = "outputs_pdfs") -> str:
    os.makedirs(pasta, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    nome = f"{nome_base}_{timestamp}.pdf"
    caminho = os.path.join(pasta, nome)

    c = canvas.Canvas(caminho, pagesize=A4)
    width, height = A4

    margem_x = 40
    y = height - 50
    linha_altura = 14
    max_chars = 110  # wrap simples

    def draw_line(text: str, y_pos: float):
        c.drawString(margem_x, y_pos, text)

    for raw_line in conteudo.splitlines():
        line = raw_line.rstrip("\n")
        if line == "":
            y -= linha_altura
            if y < 60:
                c.showPage()
                y = height - 50
            continue

        # wrap simples por caractere
        while len(line) > max_chars:
            chunk = line[:max_chars]
            draw_line(chunk, y)
            y -= linha_altura
            line = line[max_chars:]
            if y < 60:
                c.showPage()
                y = height - 50

        draw_line(line, y)
        y -= linha_altura
        if y < 60:
            c.showPage()
            y = height - 50

    c.save()
    return caminho
