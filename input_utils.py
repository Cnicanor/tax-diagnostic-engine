import re
from typing import Tuple


_RE_MENSAL = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_RE_TRIMESTRAL = re.compile(r"^\d{4}-T[1-4]$")
_RE_ANUAL = re.compile(r"^\d{4}$")


def validar_periodicidade(valor: str) -> str:
    """Normaliza periodicidade para mensal/trimestral/anual com default anual."""
    v = (valor or "").strip().lower()
    if v in ("mensal", "trimestral", "anual"):
        return v
    return "anual"


def validar_competencia(periodicidade: str, competencia: str) -> Tuple[bool, str]:
    """
    Valida competência conforme periodicidade.
    Retorna (True, valor_normalizado) ou (False, mensagem_erro).
    """
    p = validar_periodicidade(periodicidade)
    c = (competencia or "").strip().upper()

    if p == "mensal":
        if _RE_MENSAL.match(c):
            return True, c
        return False, "Competência inválida para periodicidade mensal. Use formato YYYY-MM."

    if p == "trimestral":
        if _RE_TRIMESTRAL.match(c):
            return True, c
        return False, "Competência inválida para periodicidade trimestral. Use formato YYYY-T1..T4."

    if _RE_ANUAL.match(c):
        return True, c
    return False, "Competência inválida para periodicidade anual. Use formato YYYY."


def ler_aliquota(prompt: str) -> float:
    """
    Aceita:
      - 13
      - 13%
      - 0.13
      - 8,5
    Retorna decimal: 0.13
    """
    while True:
        raw = input(prompt).strip()
        raw = raw.replace("%", "").replace(",", ".")
        try:
            v = float(raw)
            if v > 1:
                v = v / 100
            if v < 0:
                print("A alíquota não pode ser negativa.")
                continue
            return v
        except ValueError:
            print("Entrada inválida. Exemplos: 13, 13%, 0.13, 8,5%")
