from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Tuple

from audit_metadata import build_audit_metadata
from company_profile import normalize_company_profile
from dto import DiagnosticInput, DiagnosticOutput, ScenarioResult
from recommendation_engine import build_recommendation
from regime_utils import (
    REGIME_CODE_PRESUMIDO,
    REGIME_CODE_REAL,
    REGIME_CODE_SIMPLES,
    REGIME_MODEL_MANUAL,
    REGIME_MODEL_TABELADO,
    canonicalize_regime,
)
from report_builder import montar_relatorio_executivo
from report_formatters import (
    render_comparativo_section,
    render_detalhes_regime,
    render_eligibilidade_section,
    render_recomendacao_section,
)
from regimes import (
    TRIBUTOS_DAS,
    imposto_lucro_presumido,
    imposto_lucro_real_estimado_completo,
    imposto_simples,
    imposto_simples_tabelado,
    presuncao_por_tipo_atividade,
)
from ruleset_loader import DEFAULT_RULESET_ID, get_presumido_params, get_real_params, get_simples_tables
from scenarios import gerar_cenarios_reforma

PERIODICIDADES_VALIDAS = ("mensal", "trimestral", "anual")


def calcular_imposto(receita_anual: float, aliquota: float) -> float:
    return receita_anual * aliquota


class DiagnosticService:
    """
    Service Layer: orquestra regime -> cenarios -> classificacao -> relatorio.
    UI (CLI/Streamlit) apenas coleta inputs e exibe outputs.
    """

    @staticmethod
    def _classificar_impacto(diferenca: float, receita: float) -> Tuple[float, str]:
        impacto_percentual = (diferenca / receita) * 100

        if impacto_percentual < 5:
            return impacto_percentual, "Baixo impacto"
        if impacto_percentual < 12:
            return impacto_percentual, "Impacto moderado"
        return impacto_percentual, "Alto impacto"

    @staticmethod
    def _recomendacao(classificacao: str) -> str:
        if classificacao == "Baixo impacto":
            return "Monitorar mudancas e manter estrategia atual."
        if classificacao == "Impacto moderado":
            return "Revisar estrutura de custos e avaliar ajuste gradual de precos."
        return "Revisao urgente de precificacao, capital de giro e planejamento tributario."

    @staticmethod
    def _normalizar_periodicidade(periodicidade: Any) -> str:
        valor = str(periodicidade or "anual").strip().lower()
        if valor in PERIODICIDADES_VALIDAS:
            return valor
        return "anual"

    @staticmethod
    def _resolve_ruleset_id(inp: DiagnosticInput) -> str:
        if isinstance(inp.ruleset_id, str) and inp.ruleset_id.strip():
            return inp.ruleset_id.strip()
        return DEFAULT_RULESET_ID

    @staticmethod
    def _required_float(
        payload: Dict[str, Any],
        key: str,
        *,
        ruleset_id: str,
        section: str,
        regime: str,
        impacto: str,
    ) -> float:
        if key not in payload:
            raise ValueError(
                f"ruleset_id={ruleset_id} | arquivo={section} | chave={key} | "
                f"regime={regime} | impacto={impacto} | detalhe=chave ausente"
            )
        value = payload.get(key)
        if not isinstance(value, (int, float)):
            raise ValueError(
                f"ruleset_id={ruleset_id} | arquivo={section} | chave={key} | "
                f"regime={regime} | impacto={impacto} | detalhe=valor nao numerico"
            )
        return float(value)

    @staticmethod
    def _required_dict(
        payload: Dict[str, Any],
        key: str,
        *,
        ruleset_id: str,
        section: str,
        regime: str,
        impacto: str,
    ) -> Dict[str, Any]:
        if key not in payload:
            raise ValueError(
                f"ruleset_id={ruleset_id} | arquivo={section} | chave={key} | "
                f"regime={regime} | impacto={impacto} | detalhe=chave ausente"
            )
        value = payload.get(key)
        if not isinstance(value, dict):
            raise ValueError(
                f"ruleset_id={ruleset_id} | arquivo={section} | chave={key} | "
                f"regime={regime} | impacto={impacto} | detalhe=objeto invalido"
            )
        return value

    @staticmethod
    def _bloco_partilha_simples(detalhes_regime: Dict[str, Any]) -> str:
        linhas = ["=== SIMPLES NACIONAL — PARTILHA DO DAS (ESTIMATIVA) ==="]
        percentuais = detalhes_regime.get("breakdown_percentuais")
        valores = detalhes_regime.get("breakdown_das")

        if not isinstance(percentuais, dict) or not isinstance(valores, dict):
            linhas.append("partilha indisponível (evento legado)")
            return "\n".join(linhas) + "\n"

        linhas.append("Tributo | Percentual | Valor (R$)")
        linhas.append("-----------------------------------")
        for tributo in TRIBUTOS_DAS:
            p_raw = percentuais.get(tributo, 0.0)
            v_raw = valores.get(tributo, 0.0)
            try:
                p = float(p_raw)
            except (TypeError, ValueError):
                p = 0.0
            try:
                v = float(v_raw)
            except (TypeError, ValueError):
                v = 0.0
            linhas.append(f"{tributo} | {round(p * 100, 4)}% | R$ {v:,.2f}")
        return "\n".join(linhas) + "\n"

    @staticmethod
    def _formatar_data_hora_br(iso_text: Any) -> str | None:
        if not iso_text:
            return None
        try:
            dt = datetime.fromisoformat(str(iso_text))
        except (TypeError, ValueError):
            return None
        return dt.strftime("%d/%m/%Y %H:%M:%S")

    @staticmethod
    def _bloco_auditoria(audit: Dict[str, Any]) -> str:
        ruleset_metadata = audit.get("ruleset_metadata") if isinstance(audit.get("ruleset_metadata"), dict) else {}
        ruleset_id = str(audit.get("ruleset_id", ruleset_metadata.get("ruleset_id", "N/D")))
        vigencia_inicio = ruleset_metadata.get("vigencia_inicio", "N/D")
        vigencia_fim = ruleset_metadata.get("vigencia_fim", "N/D")
        descricao_ruleset = ruleset_metadata.get("descricao", "N/D")
        as_of_date = str(audit.get("as_of_date", "N/D"))
        calculo_tipo = str(audit.get("calculo_tipo", "N/D"))
        generated_at = str(audit.get("generated_at", "N/D"))

        integrity = audit.get("integrity") if isinstance(audit.get("integrity"), dict) else {}
        integrity_status = integrity.get("status", "N/D")
        integrity_ruleset_hash = integrity.get("ruleset_hash", "N/D")
        integrity_baseline_hash = integrity.get("baseline_hash", "N/D")
        checked_files = integrity.get("checked_files", []) if isinstance(integrity.get("checked_files"), list) else []

        sources = audit.get("sources") if isinstance(audit.get("sources"), list) else []
        references = audit.get("references") if isinstance(audit.get("references"), list) else []
        assumptions = audit.get("assumptions") if isinstance(audit.get("assumptions"), list) else []
        limitations = audit.get("limitations") if isinstance(audit.get("limitations"), list) else []
        alerts = audit.get("alerts") if isinstance(audit.get("alerts"), list) else []

        linhas = [
            "=== AUDITORIA (BASE NORMATIVA & PREMISSAS) ===",
            f"Ruleset: {ruleset_id}",
            f"Vigencia: {vigencia_inicio} ate {vigencia_fim}",
            f"Descricao do ruleset: {descricao_ruleset}",
            f"As of date: {as_of_date}",
            f"Tipo de calculo: {calculo_tipo}",
            f"Gerado em (ISO): {generated_at}",
            f"Integridade ruleset/baseline: {integrity_status}",
            f"Hash ruleset: {integrity_ruleset_hash}",
            f"Hash baseline: {integrity_baseline_hash}",
            f"Arquivos verificados: {', '.join(checked_files) if checked_files else 'N/D'}",
            "Fontes:",
        ]
        linhas.extend(f"- {s}" for s in sources)
        if references:
            linhas.append("Referencias oficiais:")
            linhas.extend(f"- {r}" for r in references)
        linhas.append("Premissas:")
        linhas.extend(f"- {s}" for s in assumptions)
        linhas.append("Limitacoes:")
        linhas.extend(f"- {s}" for s in limitations)
        if alerts:
            linhas.append("Alertas:")
            linhas.extend(f"- {s}" for s in alerts)
        return "\n".join(linhas)

    @staticmethod
    def _rodape_relatorio(audit: Dict[str, Any] | None) -> str:
        if not isinstance(audit, dict):
            return "Relatorio gerado em: (nao disponivel — evento legado)"
        data_hora = DiagnosticService._formatar_data_hora_br(audit.get("generated_at"))
        if not data_hora:
            return "Relatorio gerado em: (nao disponivel — evento legado)"
        return f"Relatorio gerado em: {data_hora}"

    @staticmethod
    def _imposto_atual_por_regime(inp: DiagnosticInput) -> Tuple[float, Dict[str, Any]]:
        ruleset_id = DiagnosticService._resolve_ruleset_id(inp)
        periodicidade_aplicada = DiagnosticService._normalizar_periodicidade(inp.periodicidade)
        regime_info = canonicalize_regime(inp.regime, inp.regime_code, inp.regime_model)

        regime_code = regime_info["regime_code"]
        regime_model = regime_info["regime_model"]

        if regime_code == REGIME_CODE_SIMPLES:
            if regime_model == REGIME_MODEL_MANUAL:
                if inp.aliquota_simples is None:
                    raise ValueError("Evento manual do Simples requer aliquota_simples informada.")
                return imposto_simples(inp.receita_anual, float(inp.aliquota_simples)), {
                    "aliquota_efetiva": float(inp.aliquota_simples),
                    "modelo": "manual_aliquota_informada",
                    "regime_code": regime_code,
                    "regime_model": regime_model,
                    "regime_display": regime_info["regime_display"],
                    "ruleset_id": ruleset_id,
                }

            tabelas = get_simples_tables(ruleset_id)
            receita_base = float(inp.receita_base_periodo) if inp.receita_base_periodo is not None else float(inp.receita_anual)
            rbt12 = float(inp.rbt12) if inp.rbt12 is not None else float(inp.receita_anual)
            anexo = str(inp.anexo_simples or "").strip()
            if not anexo:
                raise ValueError(
                    "ruleset_id="
                    + ruleset_id
                    + " | arquivo=simples_tables.json | chave=anexo_simples | regime=Simples Nacional | "
                    "impacto=Nao e possivel calcular DAS | detalhe=input obrigatorio ausente"
                )
            limite_elegibilidade = DiagnosticService._required_float(
                tabelas,
                "limite_elegibilidade_simples",
                ruleset_id=ruleset_id,
                section="simples_tables.json",
                regime="Simples Nacional",
                impacto="Nao e possivel validar elegibilidade do Simples",
            )
            fator_r_limite = DiagnosticService._required_float(
                tabelas,
                "fator_r_limite",
                ruleset_id=ruleset_id,
                section="simples_tables.json",
                regime="Simples Nacional",
                impacto="Nao e possivel determinar anexo III/V",
            )
            imposto, calc = imposto_simples_tabelado(
                receita_base=receita_base,
                rbt12=rbt12,
                anexo=anexo,
                tabelas=tabelas,
                fator_r=inp.fator_r,
                folha_12m=inp.folha_12m,
                limite_elegibilidade=limite_elegibilidade,
                fator_r_limite=fator_r_limite,
                ruleset_id=ruleset_id,
            )
            detalhes = {
                "modelo": "simples_tabelado_anexo_faixa",
                "regime_code": regime_code,
                "regime_model": regime_model,
                "regime_display": regime_info["regime_display"],
                "ruleset_id": ruleset_id,
                **calc,
            }
            return imposto, detalhes

        if regime_code == REGIME_CODE_PRESUMIDO:
            params = get_presumido_params(ruleset_id)
            tipo_atividade = (inp.tipo_atividade or "").strip()

            percentual_map = DiagnosticService._required_dict(
                params,
                "percentual_presuncao",
                ruleset_id=ruleset_id,
                section="presumido_params.json",
                regime="Lucro Presumido",
                impacto="Nao e possivel definir base presumida por atividade",
            )
            percentual_presuncao = presuncao_por_tipo_atividade(
                tipo_atividade if tipo_atividade else None,
                percentual_map,
                fallback_key="Comercio",
            )

            limites = DiagnosticService._required_dict(
                params,
                "limites_adicional_irpj",
                ruleset_id=ruleset_id,
                section="presumido_params.json",
                regime="Lucro Presumido",
                impacto="Nao e possivel calcular adicional de IRPJ",
            )
            if periodicidade_aplicada not in limites:
                raise ValueError(
                    f"ruleset_id={ruleset_id} | arquivo=presumido_params.json | chave=limites_adicional_irpj.{periodicidade_aplicada} | "
                    f"regime=Lucro Presumido | impacto=Nao e possivel calcular adicional de IRPJ | detalhe=chave ausente"
                )

            limite_utilizado = float(limites[periodicidade_aplicada])

            pis_aliquota = DiagnosticService._required_float(
                params,
                "pis",
                ruleset_id=ruleset_id,
                section="presumido_params.json",
                regime="Lucro Presumido",
                impacto="Nao e possivel calcular PIS/COFINS",
            )
            cofins_aliquota = DiagnosticService._required_float(
                params,
                "cofins",
                ruleset_id=ruleset_id,
                section="presumido_params.json",
                regime="Lucro Presumido",
                impacto="Nao e possivel calcular PIS/COFINS",
            )
            irpj_aliquota = DiagnosticService._required_float(
                params,
                "irpj",
                ruleset_id=ruleset_id,
                section="presumido_params.json",
                regime="Lucro Presumido",
                impacto="Nao e possivel calcular IRPJ",
            )
            adicional_irpj_aliquota = DiagnosticService._required_float(
                params,
                "adicional_irpj",
                ruleset_id=ruleset_id,
                section="presumido_params.json",
                regime="Lucro Presumido",
                impacto="Nao e possivel calcular adicional de IRPJ",
            )
            csll_aliquota = DiagnosticService._required_float(
                params,
                "csll",
                ruleset_id=ruleset_id,
                section="presumido_params.json",
                regime="Lucro Presumido",
                impacto="Nao e possivel calcular CSLL",
            )

            imposto = imposto_lucro_presumido(
                receita_anual=inp.receita_anual,
                pis=pis_aliquota,
                cofins=cofins_aliquota,
                percentual_presuncao=percentual_presuncao,
                limite_adicional_irpj=limite_utilizado,
                irpj=irpj_aliquota,
                adicional_irpj=adicional_irpj_aliquota,
                csll=csll_aliquota,
            )

            base_presumida = inp.receita_anual * percentual_presuncao
            excedente_adicional = max(0.0, base_presumida - limite_utilizado)

            detalhes = {
                "modelo": "presumido_ruleset",
                "regime_code": regime_code,
                "regime_model": regime_model,
                "regime_display": regime_info["regime_display"],
                "ruleset_id": ruleset_id,
                "tipo_atividade_considerado": tipo_atividade or "Nao informado",
                "percentual_presuncao": percentual_presuncao,
                "base_presumida": base_presumida,
                "aliquota_irpj": irpj_aliquota,
                "aliquota_csll": csll_aliquota,
                "aliquota_pis": pis_aliquota,
                "aliquota_cofins": cofins_aliquota,
                "irpj_calculado": base_presumida * irpj_aliquota,
                "csll_calculado": base_presumida * csll_aliquota,
                "pis_calculado": inp.receita_anual * pis_aliquota,
                "cofins_calculado": inp.receita_anual * cofins_aliquota,
                "adicional_irpj_calculado": excedente_adicional * adicional_irpj_aliquota,
                "periodicidade": periodicidade_aplicada,
                "periodicidade_aplicada_adicional_irpj": periodicidade_aplicada,
                "limite_adicional_irpj_utilizado": limite_utilizado,
            }
            if not tipo_atividade:
                detalhes["alerta_premissa"] = "tipo_atividade ausente; fallback do ruleset aplicado (Comercio)."
            elif tipo_atividade.lower() in ("outros", "outro"):
                detalhes["alerta_premissa"] = "tipo 'Outros' usando percentual definido no ruleset."
            return imposto, detalhes

        if regime_code == REGIME_CODE_REAL:
            params_real = get_real_params(ruleset_id)
            margem = inp.margem_lucro if inp.margem_lucro is not None else 0.10
            irpj = DiagnosticService._required_float(
                params_real,
                "irpj",
                ruleset_id=ruleset_id,
                section="real_params.json",
                regime="Lucro Real",
                impacto="Nao e possivel calcular IRPJ",
            )
            csll = DiagnosticService._required_float(
                params_real,
                "csll",
                ruleset_id=ruleset_id,
                section="real_params.json",
                regime="Lucro Real",
                impacto="Nao e possivel calcular CSLL",
            )
            pis_nao_cumulativo = DiagnosticService._required_float(
                params_real,
                "pis_nao_cumulativo",
                ruleset_id=ruleset_id,
                section="real_params.json",
                regime="Lucro Real",
                impacto="Nao e possivel calcular PIS nao cumulativo",
            )
            cofins_nao_cumulativo = DiagnosticService._required_float(
                params_real,
                "cofins_nao_cumulativo",
                ruleset_id=ruleset_id,
                section="real_params.json",
                regime="Lucro Real",
                impacto="Nao e possivel calcular COFINS nao cumulativo",
            )
            receita_base_periodo = float(inp.receita_base_periodo) if inp.receita_base_periodo is not None else float(inp.receita_anual)
            base_pis_cofins_usada = "receita_base_periodo" if inp.receita_base_periodo is not None else "receita_anual"

            imposto, componentes_real = imposto_lucro_real_estimado_completo(
                receita_anual=inp.receita_anual,
                receita_base_periodo=receita_base_periodo,
                margem_lucro=margem,
                irpj=irpj,
                csll=csll,
                pis_nao_cumulativo=pis_nao_cumulativo,
                cofins_nao_cumulativo=cofins_nao_cumulativo,
                despesas_creditaveis=inp.despesas_creditaveis,
                percentual_credito_estimado=inp.percentual_credito_estimado,
            )
            return imposto, {
                "margem_lucro_estimada": margem,
                "irpj": irpj,
                "csll": csll,
                "pis_nao_cumulativo": pis_nao_cumulativo,
                "cofins_nao_cumulativo": cofins_nao_cumulativo,
                "despesas_creditaveis": float(inp.despesas_creditaveis) if inp.despesas_creditaveis is not None else None,
                "percentual_credito_estimado": float(inp.percentual_credito_estimado) if inp.percentual_credito_estimado is not None else None,
                "base_pis_cofins_usada": base_pis_cofins_usada,
                "valor_base_pis_cofins": receita_base_periodo,
                **componentes_real,
                "regime_code": regime_code,
                "regime_model": regime_model,
                "regime_display": regime_info["regime_display"],
                "ruleset_id": ruleset_id,
            }

        raise ValueError("Regime invalido apos canonicalizacao.")

    def run(self, inp: DiagnosticInput) -> DiagnosticOutput:
        if not inp.nome_empresa.strip():
            raise ValueError("nome_empresa é obrigatório.")
        if inp.receita_anual <= 0:
            raise ValueError("receita_anual deve ser maior que zero.")

        profile = normalize_company_profile(inp)
        regime_info = canonicalize_regime(inp.regime, inp.regime_code, inp.regime_model)
        regime_display = regime_info["regime_display"]
        ruleset_id = self._resolve_ruleset_id(inp)

        imposto_atual, detalhes_regime = self._imposto_atual_por_regime(inp)
        detalhes_regime = dict(detalhes_regime)
        detalhes_regime["periodicidade"] = self._normalizar_periodicidade(inp.periodicidade)
        detalhes_regime["competencia"] = str(inp.competencia).strip() if inp.competencia else "Nao informada"
        detalhes_regime.setdefault("ruleset_id", ruleset_id)
        detalhes_regime.setdefault("regime_code", regime_info["regime_code"])
        detalhes_regime.setdefault("regime_model", regime_info["regime_model"])
        detalhes_regime.setdefault("regime_display", regime_display)
        if profile.assumptions:
            detalhes_regime["profile_assumptions"] = list(profile.assumptions)
        detalhes_regime["modo_analise"] = profile.modo_analise

        from regime_comparator import compare_regimes

        comparativo = compare_regimes(profile, ruleset_id)
        recommendation_snapshot = build_recommendation(profile, comparativo)
        detalhes_regime["eligibility_snapshot"] = comparativo.get("eligibility", {})
        detalhes_regime["comparison_snapshot"] = comparativo.get("rows", [])
        detalhes_regime["recommendation_snapshot"] = recommendation_snapshot

        audit = build_audit_metadata(inp, detalhes_regime)
        detalhes_regime["audit"] = audit

        cenarios = inp.cenarios if inp.cenarios else gerar_cenarios_reforma(ruleset_id)

        resultados: List[ScenarioResult] = []
        resultados_dict: List[Dict[str, Any]] = []

        for nome_cenario, aliq in cenarios.items():
            imposto_reforma = calcular_imposto(inp.receita_anual, aliq)
            diferenca = imposto_reforma - imposto_atual
            impacto_percentual, classificacao = self._classificar_impacto(diferenca, inp.receita_anual)
            recomendacao_cenario = self._recomendacao(classificacao)

            sr = ScenarioResult(
                nome_cenario=nome_cenario,
                aliquota_reforma=aliq,
                imposto_reforma=imposto_reforma,
                diferenca=diferenca,
                impacto_percentual=impacto_percentual,
                classificacao=classificacao,
                recomendacao=recomendacao_cenario,
            )
            resultados.append(sr)

            resultados_dict.append(
                {
                    "nome_cenario": nome_cenario,
                    "aliquota_reforma": aliq,
                    "imposto_reforma": imposto_reforma,
                    "diferenca": diferenca,
                    "impacto_percentual": impacto_percentual,
                    "classificacao": classificacao,
                    "recomendacao": recomendacao_cenario,
                }
            )

        relatorio = montar_relatorio_executivo(
            nome_empresa=inp.nome_empresa,
            receita_anual=inp.receita_anual,
            aliquota_atual=0.0,
            imposto_atual=imposto_atual,
            resultados=resultados_dict,
        )

        cab = f"\nRegime atual: {regime_display}\n"
        cab += f"Periodicidade considerada: {detalhes_regime.get('periodicidade', 'anual')}\n"
        cab += f"Competência: {detalhes_regime.get('competencia', 'Nao informada')}\n"
        cab += render_detalhes_regime(regime_info["regime_code"], detalhes_regime)

        if regime_info["regime_code"] == REGIME_CODE_SIMPLES and regime_info["regime_model"] == REGIME_MODEL_TABELADO:
            cab += self._bloco_partilha_simples(detalhes_regime)
        if regime_info["regime_code"] == REGIME_CODE_SIMPLES and regime_info["regime_model"] == REGIME_MODEL_MANUAL:
            cab += self._bloco_partilha_simples(detalhes_regime)
        relatorio = relatorio.replace("Receita anual informada:", cab + "Receita anual informada:", 1)
        relatorio += "\n\n" + render_eligibilidade_section(comparativo.get("eligibility", {}))
        relatorio += "\n\n" + render_comparativo_section(comparativo.get("rows", []))
        relatorio += "\n\n" + render_recomendacao_section(recommendation_snapshot)

        integrity = audit.get("integrity") if isinstance(audit, dict) else None
        if isinstance(integrity, dict) and integrity.get("status") == "FAIL":
            relatorio = "ALERTA DE INTEGRIDADE: ruleset/baseline com divergencia (compliance FAIL).\n\n" + relatorio

        relatorio += "\n\n" + self._bloco_auditoria(audit if isinstance(audit, dict) else {})
        relatorio += "\n" + self._rodape_relatorio(audit if isinstance(audit, dict) else None)

        return DiagnosticOutput(
            nome_empresa=inp.nome_empresa,
            receita_anual=inp.receita_anual,
            regime=regime_display,
            detalhes_regime=detalhes_regime,
            imposto_atual=imposto_atual,
            resultados=resultados,
            relatorio_texto=relatorio,
        )
