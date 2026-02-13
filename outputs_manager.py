import os


def listar_relatorios(pasta: str = "outputs"):
    if not os.path.exists(pasta):
        return []

    arquivos = []
    for nome in os.listdir(pasta):
        if nome.lower().endswith(".txt"):
            caminho = os.path.join(pasta, nome)
            arquivos.append((nome, os.path.getmtime(caminho)))

    arquivos.sort(key=lambda x: x[1], reverse=True)
    return [nome for nome, _ in arquivos]


def ler_relatorio(nome_arquivo: str, pasta: str = "outputs"):
    caminho = os.path.join(pasta, nome_arquivo)
    if not os.path.exists(caminho):
        return None

    with open(caminho, "r", encoding="utf-8") as f:
        return f.read()
