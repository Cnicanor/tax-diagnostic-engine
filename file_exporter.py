import os
from datetime import datetime


def salvar_relatorio_txt(conteudo: str, nome_base: str = "relatorio", pasta: str = "outputs") -> str:
    os.makedirs(pasta, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    nome = f"{nome_base}_{timestamp}.txt"
    caminho = os.path.join(pasta, nome)

    with open(caminho, "w", encoding="utf-8") as f:
        f.write(conteudo)

    return caminho
