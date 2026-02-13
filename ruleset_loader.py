import json
import os
import sys
from copy import deepcopy
from typing import Any, Dict, Tuple

DEFAULT_RULESET_ID = "BR_TAX_2026_V1"

_CACHE: Dict[Tuple[str, str], Dict[str, Any]] = {}


def _runtime_base_dir() -> str:
    """
    Resolve diretorio base para modo normal e executavel PyInstaller.
    """
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if isinstance(meipass, str) and meipass.strip():
            return meipass
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _rulesets_dir() -> str:
    return os.path.join(_runtime_base_dir(), "rulesets")


def _ruleset_dir(ruleset_id: str) -> str:
    return os.path.join(_rulesets_dir(), ruleset_id)


def _load_json(ruleset_id: str, filename: str) -> Dict[str, Any]:
    key = (ruleset_id, filename)
    if key in _CACHE:
        return deepcopy(_CACHE[key])

    ruleset_path = _ruleset_dir(ruleset_id)
    if not os.path.isdir(ruleset_path):
        raise FileNotFoundError(f"Ruleset '{ruleset_id}' não encontrado em {ruleset_path}.")

    file_path = os.path.join(ruleset_path, filename)
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Arquivo '{filename}' não encontrado para ruleset '{ruleset_id}'.")

    with open(file_path, "r", encoding="utf-8-sig") as f:
        payload = json.load(f)

    if not isinstance(payload, dict):
        raise ValueError(f"Arquivo '{filename}' do ruleset '{ruleset_id}' deve conter objeto JSON.")

    _CACHE[key] = payload
    return deepcopy(payload)


def _load_evidence_json(ruleset_id: str, filename: str) -> Dict[str, Any]:
    key = (ruleset_id, f"evidence/{filename}")
    if key in _CACHE:
        return deepcopy(_CACHE[key])

    ruleset_path = _ruleset_dir(ruleset_id)
    if not os.path.isdir(ruleset_path):
        raise FileNotFoundError(f"Ruleset '{ruleset_id}' não encontrado em {ruleset_path}.")

    file_path = os.path.join(ruleset_path, "evidence", filename)
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Arquivo de baseline '{filename}' não encontrado para ruleset '{ruleset_id}'.")

    with open(file_path, "r", encoding="utf-8-sig") as f:
        payload = json.load(f)

    if not isinstance(payload, dict):
        raise ValueError(f"Baseline '{filename}' do ruleset '{ruleset_id}' deve conter objeto JSON.")

    _CACHE[key] = payload
    return deepcopy(payload)


def load_ruleset(ruleset_id: str) -> Dict[str, Any]:
    return _load_json(ruleset_id, "metadata.json")


def get_presumido_params(ruleset_id: str) -> Dict[str, Any]:
    return _load_json(ruleset_id, "presumido_params.json")


def get_real_params(ruleset_id: str) -> Dict[str, Any]:
    return _load_json(ruleset_id, "real_params.json")


def get_simples_tables(ruleset_id: str) -> Dict[str, Any]:
    return _load_json(ruleset_id, "simples_tables.json")


def get_baseline_simples_tables(ruleset_id: str) -> Dict[str, Any]:
    return _load_evidence_json(ruleset_id, "baseline_simples_tables.json")


def get_baseline_presumido_params(ruleset_id: str) -> Dict[str, Any]:
    return _load_evidence_json(ruleset_id, "baseline_presumido_params.json")


def get_baseline_real_params(ruleset_id: str) -> Dict[str, Any]:
    return _load_evidence_json(ruleset_id, "baseline_real_params.json")


def get_eligibility_rules(ruleset_id: str) -> Dict[str, Any]:
    return _load_json(ruleset_id, "eligibility_rules.json")


def get_baseline_eligibility_rules(ruleset_id: str) -> Dict[str, Any]:
    return _load_evidence_json(ruleset_id, "baseline_eligibility_rules.json")


def get_regime_catalog(ruleset_id: str) -> Dict[str, Any]:
    return _load_json(ruleset_id, "regime_catalog.json")


def get_baseline_regime_catalog(ruleset_id: str) -> Dict[str, Any]:
    return _load_evidence_json(ruleset_id, "baseline_regime_catalog.json")


def get_thresholds(ruleset_id: str) -> Dict[str, Any]:
    return _load_json(ruleset_id, "thresholds.json")


def get_baseline_thresholds(ruleset_id: str) -> Dict[str, Any]:
    return _load_evidence_json(ruleset_id, "baseline_thresholds.json")
