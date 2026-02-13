from __future__ import annotations

from typing import Any, Dict, Optional

REGIME_CODE_SIMPLES = "SIMPLES"
REGIME_CODE_PRESUMIDO = "PRESUMIDO"
REGIME_CODE_REAL = "REAL"

REGIME_DISPLAY_SIMPLES = "Simples Nacional"
REGIME_DISPLAY_PRESUMIDO = "Lucro Presumido"
REGIME_DISPLAY_REAL = "Lucro Real"

REGIME_MODEL_TABELADO = "tabelado"
REGIME_MODEL_MANUAL = "manual"
REGIME_MODEL_PADRAO = "padrao"


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_text_lower(value: Any) -> str:
    return _normalize_text(value).lower()


def _from_regime_code(regime_code: Optional[str], regime_model: Optional[str]) -> Optional[Dict[str, str]]:
    code = _normalize_text(regime_code).upper()
    model = _normalize_text_lower(regime_model)
    if code == REGIME_CODE_SIMPLES:
        if model not in (REGIME_MODEL_TABELADO, REGIME_MODEL_MANUAL):
            model = REGIME_MODEL_TABELADO
        return {"regime_code": REGIME_CODE_SIMPLES, "regime_model": model, "regime_display": REGIME_DISPLAY_SIMPLES}
    if code == REGIME_CODE_PRESUMIDO:
        return {
            "regime_code": REGIME_CODE_PRESUMIDO,
            "regime_model": REGIME_MODEL_PADRAO,
            "regime_display": REGIME_DISPLAY_PRESUMIDO,
        }
    if code == REGIME_CODE_REAL:
        return {
            "regime_code": REGIME_CODE_REAL,
            "regime_model": REGIME_MODEL_PADRAO,
            "regime_display": REGIME_DISPLAY_REAL,
        }
    return None


def canonicalize_regime(
    regime: Any,
    regime_code: Optional[str] = None,
    regime_model: Optional[str] = None,
) -> Dict[str, str]:
    """
    Canonicaliza regime para contrato interno único:
    - regime_code: SIMPLES|PRESUMIDO|REAL
    - regime_model: tabelado|manual|padrao
    - regime_display: rótulo único de UI/relatório
    """
    by_code = _from_regime_code(regime_code, regime_model)
    if by_code:
        return by_code

    raw = _normalize_text(regime)
    raw_l = raw.lower()

    if raw in (REGIME_DISPLAY_SIMPLES,):
        model = _normalize_text_lower(regime_model) or REGIME_MODEL_TABELADO
        if model not in (REGIME_MODEL_TABELADO, REGIME_MODEL_MANUAL):
            model = REGIME_MODEL_TABELADO
        return {"regime_code": REGIME_CODE_SIMPLES, "regime_model": model, "regime_display": REGIME_DISPLAY_SIMPLES}

    if "simples nacional (v1" in raw_l:
        return {
            "regime_code": REGIME_CODE_SIMPLES,
            "regime_model": REGIME_MODEL_MANUAL,
            "regime_display": REGIME_DISPLAY_SIMPLES,
        }

    if "simples nacional (v2" in raw_l:
        return {
            "regime_code": REGIME_CODE_SIMPLES,
            "regime_model": REGIME_MODEL_TABELADO,
            "regime_display": REGIME_DISPLAY_SIMPLES,
        }

    if raw in (REGIME_DISPLAY_PRESUMIDO,) or "lucro presumido (v1" in raw_l:
        return {
            "regime_code": REGIME_CODE_PRESUMIDO,
            "regime_model": REGIME_MODEL_PADRAO,
            "regime_display": REGIME_DISPLAY_PRESUMIDO,
        }

    if raw in (REGIME_DISPLAY_REAL,) or "lucro real (estimado v1" in raw_l:
        return {
            "regime_code": REGIME_CODE_REAL,
            "regime_model": REGIME_MODEL_PADRAO,
            "regime_display": REGIME_DISPLAY_REAL,
        }

    return {"regime_code": REGIME_CODE_SIMPLES, "regime_model": REGIME_MODEL_TABELADO, "regime_display": REGIME_DISPLAY_SIMPLES}

