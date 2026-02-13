from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Sequence

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ruleset_loader import (
    DEFAULT_RULESET_ID,
    get_baseline_eligibility_rules,
    get_baseline_regime_catalog,
    get_baseline_presumido_params,
    get_baseline_real_params,
    get_baseline_simples_tables,
    get_baseline_thresholds,
    get_eligibility_rules,
    get_regime_catalog,
    get_presumido_params,
    get_real_params,
    get_simples_tables,
    get_thresholds,
    load_ruleset,
)

SIMPLES_ANEXOS_ESPERADOS = ("I", "II", "III", "IV", "V")
TRIBUTOS_PARTILHA_ESPERADOS = ("IRPJ", "CSLL", "PIS", "COFINS", "CPP", "ICMS", "ISS")
PARTILHA_SOMA_TOLERANCIA = 1e-6
PRESUMIDO_CHAVES_OBRIGATORIAS = (
    "pis",
    "cofins",
    "irpj",
    "adicional_irpj",
    "csll",
    "limites_adicional_irpj",
    "percentual_presuncao",
)
REAL_CHAVES_OBRIGATORIAS = (
    "irpj",
    "csll",
    "pis_nao_cumulativo",
    "cofins_nao_cumulativo",
)

CHECKED_FILES = (
    "simples_tables.json",
    "presumido_params.json",
    "real_params.json",
    "eligibility_rules.json",
    "regime_catalog.json",
    "thresholds.json",
)


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str  # PASS | FAIL
    expected: Any = None
    actual: Any = None
    details: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "expected": self.expected,
            "actual": self.actual,
            "details": self.details,
        }


def _pass(name: str, details: str = "", expected: Any = None, actual: Any = None) -> CheckResult:
    return CheckResult(name=name, status="PASS", details=details, expected=expected, actual=actual)


def _fail(name: str, details: str = "", expected: Any = None, actual: Any = None) -> CheckResult:
    return CheckResult(name=name, status="FAIL", details=details, expected=expected, actual=actual)


def _is_non_negative_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and value >= 0


def _hash_json_payload(payload: Dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _hash_composite(items: Dict[str, str]) -> str:
    canonical = json.dumps(items, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _diff_json(expected: Any, actual: Any, path: str = "$") -> List[Dict[str, Any]]:
    diffs: List[Dict[str, Any]] = []

    if type(expected) is not type(actual):
        diffs.append({"path": path, "expected": expected, "actual": actual, "details": "type mismatch"})
        return diffs

    if isinstance(expected, dict):
        expected_keys = set(expected.keys())
        actual_keys = set(actual.keys())

        for missing_key in sorted(expected_keys - actual_keys):
            diffs.append(
                {
                    "path": f"{path}.{missing_key}",
                    "expected": expected[missing_key],
                    "actual": "<missing>",
                    "details": "missing key in atual",
                }
            )
        for extra_key in sorted(actual_keys - expected_keys):
            diffs.append(
                {
                    "path": f"{path}.{extra_key}",
                    "expected": "<missing>",
                    "actual": actual[extra_key],
                    "details": "extra key em atual",
                }
            )

        for key in sorted(expected_keys & actual_keys):
            diffs.extend(_diff_json(expected[key], actual[key], f"{path}.{key}"))
        return diffs

    if isinstance(expected, list):
        if len(expected) != len(actual):
            diffs.append(
                {
                    "path": path,
                    "expected": f"len={len(expected)}",
                    "actual": f"len={len(actual)}",
                    "details": "list length mismatch",
                }
            )
            return diffs
        for idx, (exp_item, act_item) in enumerate(zip(expected, actual)):
            diffs.extend(_diff_json(exp_item, act_item, f"{path}[{idx}]"))
        return diffs

    if expected != actual:
        diffs.append({"path": path, "expected": expected, "actual": actual, "details": "value mismatch"})

    return diffs


def _simples_sentinels(metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    audit_cfg = metadata.get("audit_sentinels")
    if not isinstance(audit_cfg, dict):
        return []
    sentinels = audit_cfg.get("simples")
    if not isinstance(sentinels, list):
        return []
    valid: List[Dict[str, Any]] = []
    for item in sentinels:
        if isinstance(item, dict):
            valid.append(item)
    return valid


def validate_simples_tables(simples_tables: Dict[str, Any], simples_sentinels: Sequence[Dict[str, Any]] | None = None) -> List[CheckResult]:
    checks: List[CheckResult] = []
    anexos = simples_tables.get("anexos")
    if not isinstance(anexos, dict):
        return [_fail("Simples: estrutura anexos", expected="dict", actual=type(anexos).__name__)]

    limite_elegibilidade = simples_tables.get("limite_elegibilidade_simples")
    if _is_non_negative_number(limite_elegibilidade):
        checks.append(_pass("Simples: limite_elegibilidade_simples presente e valido"))
    else:
        checks.append(
            _fail(
                "Simples: limite_elegibilidade_simples presente e valido",
                expected="numero >= 0",
                actual=limite_elegibilidade,
            )
        )

    partilha_base = simples_tables.get("partilha_percentual_base")
    if partilha_base == "decimal_0_1":
        checks.append(_pass("Simples: partilha_percentual_base definido como decimal_0_1"))
    else:
        checks.append(
            _fail(
                "Simples: partilha_percentual_base definido como decimal_0_1",
                expected="decimal_0_1",
                actual=partilha_base,
            )
        )

    fator_r_limite = simples_tables.get("fator_r_limite")
    if _is_non_negative_number(fator_r_limite) and float(fator_r_limite) <= 1:
        checks.append(_pass("Simples: fator_r_limite presente e valido"))
    else:
        checks.append(
            _fail(
                "Simples: fator_r_limite presente e valido",
                expected="numero >= 0 e <= 1",
                actual=fator_r_limite,
            )
        )

    for anexo in SIMPLES_ANEXOS_ESPERADOS:
        faixas = anexos.get(anexo)
        if not isinstance(faixas, list):
            checks.append(
                _fail(
                    f"Simples: anexo {anexo} existe",
                    expected="lista de 6 faixas",
                    actual=type(faixas).__name__,
                )
            )
            continue

        if len(faixas) != 6:
            checks.append(
                _fail(
                    f"Simples: anexo {anexo} possui 6 faixas",
                    expected=6,
                    actual=len(faixas),
                )
            )
        else:
            checks.append(_pass(f"Simples: anexo {anexo} possui 6 faixas", expected=6, actual=6))

        limites: List[float] = []
        invalid_numbers = False
        for idx, faixa in enumerate(faixas, start=1):
            limite = faixa.get("limite_superior") if isinstance(faixa, dict) else None
            aliq = faixa.get("aliquota_nominal") if isinstance(faixa, dict) else None
            pd = faixa.get("parcela_deduzir") if isinstance(faixa, dict) else None

            if not _is_non_negative_number(limite):
                invalid_numbers = True
                checks.append(
                    _fail(
                        f"Simples: anexo {anexo} faixa {idx} limite valido",
                        expected="numero >= 0",
                        actual=limite,
                    )
                )
            else:
                limites.append(float(limite))

            if not _is_non_negative_number(aliq):
                invalid_numbers = True
                checks.append(
                    _fail(
                        f"Simples: anexo {anexo} faixa {idx} aliquota nominal valida",
                        expected="numero >= 0",
                        actual=aliq,
                    )
                )
            if not _is_non_negative_number(pd):
                invalid_numbers = True
                checks.append(
                    _fail(
                        f"Simples: anexo {anexo} faixa {idx} parcela deduzir valida",
                        expected="numero >= 0",
                        actual=pd,
                    )
                )

            partilha = faixa.get("percentuais_partilha") if isinstance(faixa, dict) else None
            if not isinstance(partilha, dict):
                invalid_numbers = True
                checks.append(
                    _fail(
                        f"Simples: anexo {anexo} faixa {idx} percentuais_partilha valido",
                        expected="objeto com IRPJ/CSLL/PIS/COFINS/CPP/ICMS/ISS",
                        actual=type(partilha).__name__,
                    )
                )
            else:
                soma_partilha = 0.0
                partilha_ok = True
                for tributo in TRIBUTOS_PARTILHA_ESPERADOS:
                    valor_tributo = partilha.get(tributo)
                    if not isinstance(valor_tributo, (int, float)):
                        partilha_ok = False
                        checks.append(
                            _fail(
                                f"Simples: anexo {anexo} faixa {idx} partilha.{tributo} valida",
                                expected="numero >= 0",
                                actual=valor_tributo,
                            )
                        )
                        continue
                    if float(valor_tributo) < 0:
                        partilha_ok = False
                        checks.append(
                            _fail(
                                f"Simples: anexo {anexo} faixa {idx} partilha.{tributo} valida",
                                expected="numero >= 0",
                                actual=valor_tributo,
                            )
                        )
                        continue
                    soma_partilha += float(valor_tributo)
                if partilha_ok:
                    if abs(soma_partilha - 1.0) <= PARTILHA_SOMA_TOLERANCIA:
                        checks.append(_pass(f"Simples: anexo {anexo} faixa {idx} partilha soma 1.0"))
                    else:
                        checks.append(
                            _fail(
                                f"Simples: anexo {anexo} faixa {idx} partilha soma 1.0",
                                expected=1.0,
                                actual=soma_partilha,
                            )
                        )

        if not invalid_numbers:
            checks.append(_pass(f"Simples: anexo {anexo} valores nao negativos"))

        crescente = all(limites[i] > limites[i - 1] for i in range(1, len(limites)))
        if len(limites) == len(faixas) and crescente:
            checks.append(_pass(f"Simples: anexo {anexo} limites crescentes"))
        else:
            checks.append(
                _fail(
                    f"Simples: anexo {anexo} limites crescentes",
                    expected="estritamente crescente",
                    actual=limites,
                )
            )

    for sentinel in simples_sentinels or []:
        anexo = str(sentinel.get("anexo", "")).strip()
        faixa_1based_raw = sentinel.get("faixa")
        expected_aliq = sentinel.get("aliquota_nominal")
        expected_pd = sentinel.get("parcela_deduzir")
        expected_partilha = sentinel.get("percentuais_partilha")

        if not anexo or not isinstance(faixa_1based_raw, int) or faixa_1based_raw <= 0:
            checks.append(
                _fail(
                    "Sentinela Simples: estrutura",
                    details=f"Sentinela inválida: {sentinel}",
                )
            )
            continue
        faixa_1based = faixa_1based_raw
        faixas = anexos.get(anexo)
        if not isinstance(faixas, list) or len(faixas) < faixa_1based:
            checks.append(
                _fail(
                    f"Sentinela Simples: Anexo {anexo} faixa {faixa_1based}",
                    details="Faixa nao encontrada.",
                )
            )
            continue
        faixa = faixas[faixa_1based - 1]
        actual_aliq = faixa.get("aliquota_nominal")
        actual_pd = faixa.get("parcela_deduzir")
        aliq_ok = isinstance(actual_aliq, (int, float)) and isinstance(expected_aliq, (int, float)) and abs(float(actual_aliq) - float(expected_aliq)) < 1e-9
        pd_ok = isinstance(actual_pd, (int, float)) and isinstance(expected_pd, (int, float)) and abs(float(actual_pd) - float(expected_pd)) < 1e-9
        if aliq_ok and pd_ok:
            checks.append(
                _pass(
                    f"Sentinela Simples: Anexo {anexo} faixa {faixa_1based}",
                    expected={"aliquota_nominal": expected_aliq, "parcela_deduzir": expected_pd},
                    actual={"aliquota_nominal": actual_aliq, "parcela_deduzir": actual_pd},
                )
            )
        else:
            checks.append(
                _fail(
                    f"Sentinela Simples: Anexo {anexo} faixa {faixa_1based}",
                    expected={"aliquota_nominal": expected_aliq, "parcela_deduzir": expected_pd},
                    actual={"aliquota_nominal": actual_aliq, "parcela_deduzir": actual_pd},
                )
            )

        faixas_partilha = anexos.get(anexo)
        if not isinstance(faixas_partilha, list) or len(faixas_partilha) < faixa_1based:
            checks.append(
                _fail(
                    f"Sentinela Simples Partilha: Anexo {anexo} faixa {faixa_1based}",
                    details="Faixa nao encontrada.",
                )
            )
            continue
        faixa_partilha = faixas_partilha[faixa_1based - 1]
        actual_partilha = faixa_partilha.get("percentuais_partilha") if isinstance(faixa_partilha, dict) else None
        if not isinstance(actual_partilha, dict) or not isinstance(expected_partilha, dict):
            checks.append(
                _fail(
                    f"Sentinela Simples Partilha: Anexo {anexo} faixa {faixa_1based}",
                    expected=expected_partilha,
                    actual=actual_partilha,
                )
            )
            continue
        partilha_ok = True
        for tributo, expected_value in expected_partilha.items():
            actual_value = actual_partilha.get(tributo)
            if not isinstance(actual_value, (int, float)) or not isinstance(expected_value, (int, float)):
                partilha_ok = False
                break
            if abs(float(actual_value) - float(expected_value)) > 1e-9:
                partilha_ok = False
                break
        if partilha_ok:
            checks.append(
                _pass(
                    f"Sentinela Simples Partilha: Anexo {anexo} faixa {faixa_1based}",
                    expected=expected_partilha,
                    actual=actual_partilha,
                )
            )
        else:
            checks.append(
                _fail(
                    f"Sentinela Simples Partilha: Anexo {anexo} faixa {faixa_1based}",
                    expected=expected_partilha,
                    actual=actual_partilha,
                )
            )

    return checks


def validate_required_keys(payload: Dict[str, Any], section_name: str, required_keys: Sequence[str]) -> List[CheckResult]:
    checks: List[CheckResult] = []
    for key in required_keys:
        if key in payload:
            checks.append(_pass(f"{section_name}: chave obrigatoria '{key}'"))
        else:
            checks.append(_fail(f"{section_name}: chave obrigatoria '{key}'", expected="presente", actual="ausente"))
    return checks


def validate_real_params_ranges(real_params: Dict[str, Any]) -> tuple[List[CheckResult], List[str]]:
    checks: List[CheckResult] = []
    warnings: List[str] = []

    for key in ("pis_nao_cumulativo", "cofins_nao_cumulativo"):
        value = real_params.get(key)
        if not isinstance(value, (int, float)):
            checks.append(
                _fail(
                    f"Real: faixa valida para '{key}'",
                    expected="numero entre 0 e 1",
                    actual=value,
                )
            )
            continue
        numeric = float(value)
        if 0.0 <= numeric <= 1.0:
            checks.append(_pass(f"Real: faixa valida para '{key}'"))
        else:
            checks.append(
                _fail(
                    f"Real: faixa valida para '{key}'",
                    expected="numero entre 0 e 1",
                    actual=numeric,
                )
            )

    pis = real_params.get("pis_nao_cumulativo")
    cofins = real_params.get("cofins_nao_cumulativo")
    if isinstance(pis, (int, float)) and isinstance(cofins, (int, float)):
        soma = float(pis) + float(cofins)
        if soma > 0.2:
            warnings.append(
                f"WARNING: Real params com soma de PIS+COFINS acima de 0.2 ({soma})."
            )

    return checks, warnings


def validate_eligibility_rules(payload: Dict[str, Any]) -> List[CheckResult]:
    checks: List[CheckResult] = []
    for regime_key in ("simples", "presumido", "real"):
        if regime_key not in payload or not isinstance(payload.get(regime_key), dict):
            checks.append(
                _fail(
                    f"Eligibility: seção '{regime_key}'",
                    expected="objeto presente",
                    actual=type(payload.get(regime_key)).__name__,
                )
            )
            continue
        checks.append(_pass(f"Eligibility: seção '{regime_key}'"))

    simples = payload.get("simples", {})
    if isinstance(simples, dict):
        rbt12_max = simples.get("rbt12_max")
        if isinstance(rbt12_max, (int, float)) and float(rbt12_max) > 0:
            checks.append(_pass("Eligibility Simples: rbt12_max válido"))
        else:
            checks.append(_fail("Eligibility Simples: rbt12_max válido", expected="numero > 0", actual=rbt12_max))

    presumido = payload.get("presumido", {})
    if isinstance(presumido, dict):
        receita_anual_max = presumido.get("receita_anual_max")
        if isinstance(receita_anual_max, (int, float)) and float(receita_anual_max) > 0:
            checks.append(_pass("Eligibility Presumido: receita_anual_max válido"))
        else:
            checks.append(
                _fail(
                    "Eligibility Presumido: receita_anual_max válido",
                    expected="numero > 0",
                    actual=receita_anual_max,
                )
            )

    real = payload.get("real", {})
    if isinstance(real, dict):
        warnings = real.get("warnings")
        if isinstance(warnings, list):
            checks.append(_pass("Eligibility Real: warnings em lista"))
        else:
            checks.append(_fail("Eligibility Real: warnings em lista", expected="lista", actual=type(warnings).__name__))

    return checks


def validate_regime_catalog(payload: Dict[str, Any]) -> List[CheckResult]:
    checks: List[CheckResult] = []
    regimes = payload.get("regimes")
    if not isinstance(regimes, list):
        return [_fail("Regime catalog: regimes", expected="lista", actual=type(regimes).__name__)]
    if not regimes:
        return [_fail("Regime catalog: regimes nao vazio", expected=">=1 item", actual=0)]

    required_codes = {"SIMPLES", "PRESUMIDO", "REAL"}
    found_codes: set[str] = set()
    duplicate_codes: set[str] = set()
    mandatory_keys = ("regime_code", "display_name", "enabled", "requires_fields", "notes")

    for idx, item in enumerate(regimes, start=1):
        if not isinstance(item, dict):
            checks.append(_fail(f"Regime catalog: item {idx} tipo", expected="objeto", actual=type(item).__name__))
            continue

        for key in mandatory_keys:
            if key not in item:
                checks.append(_fail(f"Regime catalog: item {idx} chave '{key}'", expected="presente", actual="ausente"))
            else:
                checks.append(_pass(f"Regime catalog: item {idx} chave '{key}'"))

        regime_code = item.get("regime_code")
        if isinstance(regime_code, str) and regime_code.strip():
            normalized = regime_code.strip().upper()
            if normalized in found_codes:
                duplicate_codes.add(normalized)
            found_codes.add(normalized)
        else:
            checks.append(_fail(f"Regime catalog: item {idx} regime_code valido", expected="string nao vazia", actual=regime_code))

        if not isinstance(item.get("enabled"), bool):
            checks.append(
                _fail(
                    f"Regime catalog: item {idx} enabled valido",
                    expected="bool",
                    actual=type(item.get("enabled")).__name__,
                )
            )
        if not isinstance(item.get("requires_fields"), list):
            checks.append(
                _fail(
                    f"Regime catalog: item {idx} requires_fields valido",
                    expected="lista",
                    actual=type(item.get("requires_fields")).__name__,
                )
            )

    missing_required = required_codes - found_codes
    if missing_required:
        checks.append(
            _fail(
                "Regime catalog: codigos obrigatorios",
                expected=sorted(required_codes),
                actual=sorted(found_codes),
                details=f"ausentes: {sorted(missing_required)}",
            )
        )
    else:
        checks.append(_pass("Regime catalog: codigos obrigatorios"))

    if duplicate_codes:
        checks.append(
            _fail(
                "Regime catalog: codigos duplicados",
                expected="sem duplicidade",
                actual=sorted(duplicate_codes),
            )
        )
    else:
        checks.append(_pass("Regime catalog: codigos duplicados"))
    return checks


def validate_thresholds(payload: Dict[str, Any]) -> List[CheckResult]:
    checks: List[CheckResult] = []
    portes = payload.get("portes")
    if not isinstance(portes, list):
        return [_fail("Thresholds: portes", expected="lista", actual=type(portes).__name__)]
    if not portes:
        return [_fail("Thresholds: portes nao vazio", expected=">=1 item", actual=0)]

    required_keys = ("porte", "ordem", "limite_receita_anual")
    limites_ordenados: List[tuple[int, float]] = []

    for idx, item in enumerate(portes, start=1):
        if not isinstance(item, dict):
            checks.append(_fail(f"Thresholds: item {idx} tipo", expected="objeto", actual=type(item).__name__))
            continue
        for key in required_keys:
            if key not in item:
                checks.append(_fail(f"Thresholds: item {idx} chave '{key}'", expected="presente", actual="ausente"))
            else:
                checks.append(_pass(f"Thresholds: item {idx} chave '{key}'"))

        ordem = item.get("ordem")
        limite = item.get("limite_receita_anual")
        if not isinstance(ordem, int) or ordem <= 0:
            checks.append(_fail(f"Thresholds: item {idx} ordem valida", expected="inteiro > 0", actual=ordem))
            continue
        if not _is_non_negative_number(limite):
            checks.append(_fail(f"Thresholds: item {idx} limite valido", expected="numero >= 0", actual=limite))
            continue
        limites_ordenados.append((ordem, float(limite)))

    if limites_ordenados:
        limites_sorted = [limite for _, limite in sorted(limites_ordenados, key=lambda x: x[0])]
        crescente = all(limites_sorted[i] > limites_sorted[i - 1] for i in range(1, len(limites_sorted)))
        if crescente:
            checks.append(_pass("Thresholds: limites crescentes por ordem"))
        else:
            checks.append(
                _fail(
                    "Thresholds: limites crescentes por ordem",
                    expected="estritamente crescente",
                    actual=limites_sorted,
                )
            )
    return checks


def audit_ruleset(ruleset_id: str = DEFAULT_RULESET_ID) -> Dict[str, Any]:
    """Executa auditoria estrutural e de integridade deterministicamente com baseline."""
    checks: List[CheckResult] = []
    warnings: List[str] = []
    metadata = load_ruleset(ruleset_id)

    ruleset_payloads = {
        "simples_tables.json": get_simples_tables(ruleset_id),
        "presumido_params.json": get_presumido_params(ruleset_id),
        "real_params.json": get_real_params(ruleset_id),
        "eligibility_rules.json": get_eligibility_rules(ruleset_id),
        "regime_catalog.json": get_regime_catalog(ruleset_id),
        "thresholds.json": get_thresholds(ruleset_id),
    }
    baseline_payloads = {
        "simples_tables.json": get_baseline_simples_tables(ruleset_id),
        "presumido_params.json": get_baseline_presumido_params(ruleset_id),
        "real_params.json": get_baseline_real_params(ruleset_id),
        "eligibility_rules.json": get_baseline_eligibility_rules(ruleset_id),
        "regime_catalog.json": get_baseline_regime_catalog(ruleset_id),
        "thresholds.json": get_baseline_thresholds(ruleset_id),
    }

    checks.extend(
        validate_simples_tables(
            ruleset_payloads["simples_tables.json"],
            simples_sentinels=_simples_sentinels(metadata),
        )
    )
    checks.extend(
        validate_required_keys(
            ruleset_payloads["presumido_params.json"],
            "Presumido",
            PRESUMIDO_CHAVES_OBRIGATORIAS,
        )
    )
    checks.extend(
        validate_required_keys(
            ruleset_payloads["real_params.json"],
            "Real",
            REAL_CHAVES_OBRIGATORIAS,
        )
    )
    real_range_checks, real_warnings = validate_real_params_ranges(ruleset_payloads["real_params.json"])
    checks.extend(real_range_checks)
    warnings.extend(real_warnings)
    checks.extend(validate_eligibility_rules(ruleset_payloads["eligibility_rules.json"]))
    checks.extend(validate_regime_catalog(ruleset_payloads["regime_catalog.json"]))
    checks.extend(validate_thresholds(ruleset_payloads["thresholds.json"]))

    json_diffs: List[Dict[str, Any]] = []
    ruleset_file_hashes: Dict[str, str] = {}
    baseline_file_hashes: Dict[str, str] = {}

    for filename in CHECKED_FILES:
        ruleset_payload = ruleset_payloads[filename]
        baseline_payload = baseline_payloads[filename]
        ruleset_file_hashes[filename] = _hash_json_payload(ruleset_payload)
        baseline_file_hashes[filename] = _hash_json_payload(baseline_payload)

        diffs = _diff_json(baseline_payload, ruleset_payload, path=f"$.{filename}")
        if diffs:
            json_diffs.extend(diffs)
            checks.append(
                _fail(
                    f"Baseline parity: {filename}",
                    expected="igual ao baseline",
                    actual=f"{len(diffs)} divergencia(s)",
                )
            )
        else:
            checks.append(_pass(f"Baseline parity: {filename}"))

    ruleset_hash = _hash_composite(ruleset_file_hashes)
    baseline_hash = _hash_composite(baseline_file_hashes)

    all_pass = all(c.status == "PASS" for c in checks)
    fail_checks = [c.to_dict() for c in checks if c.status == "FAIL"]

    return {
        "ruleset_id": ruleset_id,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "metadata": {
            "ruleset_id": metadata.get("ruleset_id"),
            "vigencia_inicio": metadata.get("vigencia_inicio"),
            "vigencia_fim": metadata.get("vigencia_fim"),
            "descricao": metadata.get("descricao"),
        },
        "checked_files": list(CHECKED_FILES),
        "ruleset_file_hashes": ruleset_file_hashes,
        "baseline_file_hashes": baseline_file_hashes,
        "ruleset_hash_sha256": ruleset_hash,
        "baseline_hash_sha256": baseline_hash,
        "overall_status": "PASS" if all_pass else "FAIL",
        "checks": [c.to_dict() for c in checks],
        "differences": fail_checks,
        "json_differences": json_diffs,
        "warnings": warnings,
    }


def get_integrity_summary(ruleset_id: str = DEFAULT_RULESET_ID) -> Dict[str, Any]:
    """Resumo curto de integridade para anexar no audit metadata do diagnóstico."""
    result = audit_ruleset(ruleset_id)
    return {
        "status": result.get("overall_status"),
        "ruleset_hash": result.get("ruleset_hash_sha256"),
        "baseline_hash": result.get("baseline_hash_sha256"),
        "checked_files": result.get("checked_files", []),
        "difference_count": len(result.get("json_differences", [])),
        "warning_count": len(result.get("warnings", [])),
    }


def render_audit_report_text(result: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("=== RULESET AUDIT REPORT (FULL) ===")
    lines.append(f"Ruleset: {result.get('ruleset_id')}")
    lines.append(f"Timestamp: {result.get('timestamp')}")
    lines.append(f"Overall: {result.get('overall_status')}")
    lines.append(f"Ruleset hash (SHA-256): {result.get('ruleset_hash_sha256')}")
    lines.append(f"Baseline hash (SHA-256): {result.get('baseline_hash_sha256')}")
    lines.append("")

    meta = result.get("metadata", {})
    lines.append("Metadata:")
    lines.append(f"- ruleset_id: {meta.get('ruleset_id')}")
    lines.append(f"- vigencia_inicio: {meta.get('vigencia_inicio')}")
    lines.append(f"- vigencia_fim: {meta.get('vigencia_fim')}")
    lines.append(f"- descricao: {meta.get('descricao')}")
    lines.append("")

    lines.append("File hashes:")
    for filename in result.get("checked_files", []):
        ruleset_h = result.get("ruleset_file_hashes", {}).get(filename)
        baseline_h = result.get("baseline_file_hashes", {}).get(filename)
        lines.append(f"- {filename}")
        lines.append(f"  ruleset : {ruleset_h}")
        lines.append(f"  baseline: {baseline_h}")

    lines.append("")
    lines.append("Warnings:")
    warnings = result.get("warnings", [])
    if not warnings:
        lines.append("- none")
    else:
        for warning in warnings:
            lines.append(f"- {warning}")
    lines.append("")
    lines.append("Checks:")
    for check in result.get("checks", []):
        lines.append(f"[{check.get('status')}] {check.get('name')}")
        expected = check.get("expected")
        actual = check.get("actual")
        details = check.get("details")
        if expected is not None or actual is not None:
            lines.append(f"  expected={expected} | actual={actual}")
        if details:
            lines.append(f"  details={details}")

    lines.append("")
    lines.append("JSON diffs (baseline vs ruleset):")
    json_diffs = result.get("json_differences", [])
    if not json_diffs:
        lines.append("- none")
    else:
        for diff in json_diffs:
            lines.append(
                f"- path={diff.get('path')} | expected={diff.get('expected')} | actual={diff.get('actual')} | details={diff.get('details')}"
            )

    return "\n".join(lines)


def write_audit_report(result: Dict[str, Any], output_dir: str = "outputs") -> str:
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    name = f"ruleset_audit_{result.get('ruleset_id', 'unknown')}_{timestamp}.txt"
    path = os.path.join(output_dir, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(render_audit_report_text(result))
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Audita integridade estrutural e paridade com baseline de um ruleset fiscal.")
    parser.add_argument("--ruleset-id", default=DEFAULT_RULESET_ID)
    parser.add_argument("--output-dir", default="outputs")
    args = parser.parse_args()

    try:
        result = audit_ruleset(args.ruleset_id)
    except Exception as exc:  # noqa: BLE001
        print(f"Erro ao auditar ruleset '{args.ruleset_id}': {exc}")
        return 2

    report_path = write_audit_report(result, output_dir=args.output_dir)
    print(f"Relatorio de auditoria gerado: {report_path}")
    print(f"Status geral: {result.get('overall_status')}")
    print(f"Ruleset hash: {result.get('ruleset_hash_sha256')}")
    print(f"Baseline hash: {result.get('baseline_hash_sha256')}")
    return 0 if result.get("overall_status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
