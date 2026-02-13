def formatar_reais(valor: float) -> str:
    # Formato simples PT-BR aproximado (console)
    try:
        s = f"{valor:,.2f}"
        # troca separadores estilo US -> BR
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {s}"
    except Exception:
        return f"R$ {valor}"


def formatar_percentual(valor: float, casas: int = 2, ja_percentual: bool = False) -> str:
    """Formata percentual em pt-BR (ex.: 11,37%)."""
    try:
        numero = float(valor)
        if not ja_percentual:
            numero *= 100.0
        s = f"{numero:,.{casas}f}"
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{s}%"
    except Exception:
        return f"{valor}%"
