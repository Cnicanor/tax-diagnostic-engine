from __future__ import annotations

from typing import Dict

from ruleset_loader import DEFAULT_RULESET_ID, load_ruleset


def gerar_cenarios_reforma(ruleset_id: str = DEFAULT_RULESET_ID) -> Dict[str, float]:
    """
    Carrega cenarios pos-reforma a partir do metadata do ruleset.
    """
    metadata = load_ruleset(ruleset_id)
    raw = metadata.get("cenarios_reforma")
    if not isinstance(raw, dict) or not raw:
        raise ValueError(
            f"ruleset_id={ruleset_id} | arquivo=metadata.json | chave=cenarios_reforma | "
            "regime=Todos | impacto=Sem cenarios padrao de simulacao | detalhe=objeto ausente/invalid"
        )

    cenarios: Dict[str, float] = {}
    for nome, valor in raw.items():
        if not isinstance(nome, str) or not nome.strip():
            raise ValueError(
                f"ruleset_id={ruleset_id} | arquivo=metadata.json | chave=cenarios_reforma | "
                "regime=Todos | impacto=Sem cenarios padrao de simulacao | detalhe=nome de cenario invalido"
            )
        if not isinstance(valor, (int, float)):
            raise ValueError(
                f"ruleset_id={ruleset_id} | arquivo=metadata.json | chave=cenarios_reforma.{nome} | "
                "regime=Todos | impacto=Sem cenarios padrao de simulacao | detalhe=aliquota nao numerica"
            )
        cenarios[nome] = float(valor)

    return cenarios
