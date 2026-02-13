import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import streamlit as st

from demo_config import demo_example_event, resolve_demo_mode, resolve_storage_targets
from dto import DiagnosticInput
from file_exporter import salvar_relatorio_txt
from history_store import (
    append_event,
    build_refreshed_event,
    get_event_report_text,
    has_audit,
    list_events,
    normalize_event,
)
from input_utils import validar_competencia, validar_periodicidade
from pdf_exporter import salvar_relatorio_pdf
from regime_utils import (
    REGIME_CODE_SIMPLES,
    REGIME_DISPLAY_PRESUMIDO,
    REGIME_DISPLAY_REAL,
    REGIME_DISPLAY_SIMPLES,
)
from ruleset_loader import DEFAULT_RULESET_ID, get_simples_tables
from scenarios import gerar_cenarios_reforma
from tax_engine import DiagnosticService


def nome_arquivo_seguro(nome_empresa: str) -> str:
    """Gera base de nome de arquivo sem caracteres especiais."""
    nome_limpo = re.sub(r"[^a-zA-Z0-9_ -]", "", (nome_empresa or ""))
    nome_limpo = nome_limpo.strip().replace(" ", "_")
    return f"relatorio_{nome_limpo or 'empresa'}"


def parse_percent(texto: str) -> float:
    t = (texto or "").strip().replace("%", "").replace(",", ".")
    if t == "":
        return 0.0
    try:
        v = float(t)
    except ValueError:
        return 0.0
    if v > 1:
        v = v / 100
    return v


def _resultados_evento(evento: Dict[str, Any]) -> List[Dict[str, Any]]:
    resultados = evento.get("resultados")
    return resultados if isinstance(resultados, list) else []


def _historico_tabela(eventos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    tabela: List[Dict[str, Any]] = []
    for evento in eventos:
        tabela.append(
            {
                "Data/Hora": evento.get("timestamp", ""),
                "Empresa": evento.get("nome_empresa", ""),
                "Regime": evento.get("regime", ""),
                "Receita (R$)": round(float(evento.get("receita_anual", 0.0)), 2),
                "Imposto atual (R$)": round(float(evento.get("imposto_atual", 0.0)), 2),
            }
        )
    return tabela


def _renderizar_resultado(evento: Dict[str, Any]) -> None:
    st.subheader("Resumo")
    st.write(f"**Empresa:** {evento.get('nome_empresa', '')}")
    st.write(f"**Regime:** {evento.get('regime', '')}")
    st.write(f"**Imposto atual (estimado):** R$ {float(evento.get('imposto_atual', 0.0)):,.2f}")

    st.subheader("Cenarios")
    st.dataframe(
        [
            {
                "Cenario": r.get("nome_cenario"),
                "Aliquota": r.get("aliquota_reforma"),
                "Imposto pos-reforma": r.get("imposto_reforma"),
                "Diferenca vs atual": r.get("diferenca"),
                "Impacto (%)": r.get("impacto_percentual"),
                "Classificacao": r.get("classificacao"),
                "Recomendacao": r.get("recomendacao"),
            }
            for r in _resultados_evento(evento)
        ],
        width="stretch",
    )

    detalhes = evento.get("detalhes_regime", {})
    if isinstance(detalhes, dict) and detalhes.get("regime_code") == REGIME_CODE_SIMPLES:
        st.subheader("Simples Nacional - Partilha do DAS (estimativa)")
        percentuais = detalhes.get("breakdown_percentuais")
        valores = detalhes.get("breakdown_das")
        if isinstance(percentuais, dict) and isinstance(valores, dict):
            linhas = []
            for tributo in ("IRPJ", "CSLL", "PIS", "COFINS", "CPP", "ICMS", "ISS"):
                linhas.append(
                    {
                        "Tributo": tributo,
                        "Percentual": round(float(percentuais.get(tributo, 0.0)) * 100, 4),
                        "Valor (R$)": round(float(valores.get(tributo, 0.0)), 2),
                    }
                )
            st.dataframe(linhas, hide_index=True, width="stretch")
        else:
            st.info("Partilha indisponível (evento legado).")


def _competencia_padrao(periodicidade: str) -> str:
    agora = datetime.now()
    p = validar_periodicidade(periodicidade)
    if p == "mensal":
        return agora.strftime("%Y-%m")
    if p == "trimestral":
        trimestre = ((agora.month - 1) // 3) + 1
        return f"{agora.year}-T{trimestre}"
    return agora.strftime("%Y")


def _competencia_placeholder(periodicidade: str) -> str:
    p = validar_periodicidade(periodicidade)
    if p == "mensal":
        return "YYYY-MM (ex: 2026-02)"
    if p == "trimestral":
        return "YYYY-Tn (ex: 2026-T1)"
    return "YYYY (ex: 2026)"


def _deve_exibir_refresh_legado(evento: Dict[str, Any]) -> bool:
    texto = evento.get("relatorio_texto")
    if not (isinstance(texto, str) and texto.strip()):
        return False
    tem_bloco_auditoria = "=== AUDITORIA" in texto
    return (not has_audit(evento)) or (not tem_bloco_auditoria)


st.set_page_config(page_title="Tax Diagnostic Engine", layout="wide")
st.title("Tax Diagnostic Engine")
st.caption("Diagnostico tributario continuo (MVP v1) para apoio a decisao.")

service = DiagnosticService()
simples_tables_default = get_simples_tables(DEFAULT_RULESET_ID)
fator_r_limite_default_raw = simples_tables_default.get("fator_r_limite")
if not isinstance(fator_r_limite_default_raw, (int, float)):
    raise ValueError(
        f"ruleset_id={DEFAULT_RULESET_ID} | arquivo=simples_tables.json | chave=fator_r_limite | "
        "regime=Simples Nacional | impacto=Default de fator R invalido na UI | detalhe=valor nao numerico"
    )
fator_r_limite_default = float(fator_r_limite_default_raw)
cenarios_default_ruleset = gerar_cenarios_reforma(DEFAULT_RULESET_ID)
cenarios_default_items = list(cenarios_default_ruleset.items())
if len(cenarios_default_items) < 3:
    raise ValueError(
        f"ruleset_id={DEFAULT_RULESET_ID} | arquivo=metadata.json | chave=cenarios_reforma | "
        "regime=Todos | impacto=UI sem cenarios padrao | detalhe=menos de 3 cenarios"
    )

if "carregado" not in st.session_state:
    st.session_state["carregado"] = None
if "ultimo_out" not in st.session_state:
    st.session_state["ultimo_out"] = None
if "evento_aberto" not in st.session_state:
    st.session_state["evento_aberto"] = None
if "demo_toggle" not in st.session_state:
    st.session_state["demo_toggle"] = False

carregado = normalize_event(st.session_state["carregado"] or {})
nome_default = carregado.get("nome_empresa", "")
receita_default = float(carregado.get("receita_anual", 0.0))
regime_default = carregado.get("regime", REGIME_DISPLAY_SIMPLES)
detalhes_default = carregado.get("detalhes_regime", {}) or {}

margem_default = float(detalhes_default.get("margem_lucro_estimada", 0.10))
tipo_atividade_default = str(detalhes_default.get("tipo_atividade_considerado", "Comercio"))
rbt12_default = float(detalhes_default.get("rbt12", receita_default or 0.0))
receita_base_default = float(detalhes_default.get("receita_base_periodo", receita_default or 0.0))
anexo_default_raw = str(detalhes_default.get("anexo_informado", detalhes_default.get("anexo_aplicado", "I")))
anexo_default = anexo_default_raw.strip().upper().replace("-", "/")
if anexo_default not in ("I", "II", "III", "IV", "V", "III/V"):
    anexo_default = "I"
fator_r_default = detalhes_default.get("fator_r")
try:
    fator_r_default = float(fator_r_default) if fator_r_default is not None else fator_r_limite_default
except (TypeError, ValueError):
    fator_r_default = fator_r_limite_default
folha_12m_default = detalhes_default.get("folha_12m")
try:
    folha_12m_default = float(folha_12m_default) if folha_12m_default is not None else 0.0
except (TypeError, ValueError):
    folha_12m_default = 0.0
periodicidade_default = validar_periodicidade(str(detalhes_default.get("periodicidade", "anual")))
competencia_default_raw = str(detalhes_default.get("competencia", ""))
competencia_default = "" if competencia_default_raw in ("", "Nao informada", "Não informada") else competencia_default_raw
if not competencia_default:
    competencia_default = _competencia_padrao(periodicidade_default)
modo_analise_default = str(detalhes_default.get("modo_analise", "conservador")).strip().lower()
if modo_analise_default not in ("conservador", "estrategico"):
    modo_analise_default = "conservador"

with st.sidebar:
    st.header("Configuracoes")
    demo_toggle = st.toggle(
        "Modo DEMO",
        value=resolve_demo_mode(toggle_enabled=False),
        key="demo_toggle",
    )
    demo_mode = resolve_demo_mode(toggle_enabled=demo_toggle)
    storage_targets = resolve_storage_targets(demo_mode)

    if demo_mode:
        st.caption("DEMO ativa: historico e exportacoes sao isolados em pastas *_demo.")
        st.markdown("---")
        st.subheader("Exemplos DEMO")

        if st.button("Carregar Exemplo - Simples Nacional", use_container_width=True, key="demo_exemplo_simples"):
            st.session_state["carregado"] = normalize_event(demo_example_event("simples"))
            st.session_state["evento_aberto"] = None
            st.session_state["ultimo_out"] = None
            st.rerun()

        if st.button("Carregar Exemplo - Lucro Presumido", use_container_width=True, key="demo_exemplo_presumido"):
            st.session_state["carregado"] = normalize_event(demo_example_event("presumido"))
            st.session_state["evento_aberto"] = None
            st.session_state["ultimo_out"] = None
            st.rerun()

        if st.button("Carregar Exemplo - Lucro Real", use_container_width=True, key="demo_exemplo_real"):
            st.session_state["carregado"] = normalize_event(demo_example_event("real"))
            st.session_state["evento_aberto"] = None
            st.session_state["ultimo_out"] = None
            st.rerun()

    st.markdown("---")

    regimes_lista = [REGIME_DISPLAY_SIMPLES, REGIME_DISPLAY_PRESUMIDO, REGIME_DISPLAY_REAL]
    regime = st.selectbox(
        "Regime atual",
        regimes_lista,
        index=regimes_lista.index(regime_default) if regime_default in regimes_lista else 0,
    )

    st.markdown("---")
    modo_labels = ["Conservador", "Estratégico"]
    modo_default_idx = 0 if modo_analise_default == "conservador" else 1
    modo_label = st.selectbox("Modo de recomendação", modo_labels, index=modo_default_idx)
    modo_analise = "conservador" if modo_label.startswith("Conservador") else "estrategico"

    st.markdown("---")
    st.subheader("Cenarios pos-reforma")
    cen_otim = st.text_input("Otimista (%)", value=str(round(float(cenarios_default_items[0][1]) * 100, 4)))
    cen_base = st.text_input("Base (%)", value=str(round(float(cenarios_default_items[1][1]) * 100, 4)))
    cen_pess = st.text_input("Pessimista (%)", value=str(round(float(cenarios_default_items[2][1]) * 100, 4)))

    st.markdown("---")
    st.subheader("Historico")

    busca = st.text_input("Buscar empresa", value="", key="historico_busca").strip().lower()
    eventos = list_events(
        limit=200,
        pasta=storage_targets["history_pasta"],
        arquivo=storage_targets["history_arquivo"],
    )

    if busca:
        eventos = [e for e in eventos if busca in (e.get("nome_empresa", "") or "").lower()]

    if not eventos:
        st.caption("Nenhuma analise encontrada.")
    else:
        tabela_historico = _historico_tabela(eventos)
        st.dataframe(tabela_historico, hide_index=True, width="stretch")

        opcoes = [
            f"{idx + 1}. {e.get('timestamp', '')} | {e.get('nome_empresa', '(sem nome)')}"
            for idx, e in enumerate(eventos)
        ]
        escolhido = st.selectbox("Selecionar analise", options=opcoes, key="historico_select")
        idx_escolhido = opcoes.index(escolhido)
        evento_escolhido = normalize_event(eventos[idx_escolhido])

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Abrir analise", use_container_width=True):
                st.session_state["evento_aberto"] = evento_escolhido
                st.session_state["carregado"] = evento_escolhido
                st.session_state["ultimo_out"] = None
                st.success("Analise salva aberta.")
                st.rerun()
        with c2:
            if st.button("Limpar", use_container_width=True):
                st.session_state["evento_aberto"] = None
                st.session_state["carregado"] = None
                st.info("Selecao limpa.")
                st.rerun()

        relatorio_salvo = get_event_report_text(evento_escolhido)
        base_historico = nome_arquivo_seguro(evento_escolhido.get("nome_empresa", "empresa")) + "_historico"

        c3, c4 = st.columns(2)
        with c3:
            if st.button("Exportar TXT salvo", use_container_width=True):
                caminho = salvar_relatorio_txt(
                    relatorio_salvo,
                    nome_base=base_historico,
                    pasta=storage_targets["outputs_txt_pasta"],
                )
                st.info(f"TXT salvo: {caminho}")
        with c4:
            if st.button("Exportar PDF salvo", use_container_width=True):
                caminho = salvar_relatorio_pdf(
                    relatorio_salvo,
                    nome_base=base_historico,
                    pasta=storage_targets["outputs_pdf_pasta"],
                )
                st.info(f"PDF salvo: {caminho}")

        if _deve_exibir_refresh_legado(evento_escolhido):
            if st.button("Regerar relatorio no formato atual (sem recalcular)", use_container_width=True):
                refreshed_event = build_refreshed_event(evento_escolhido)
                base_refresh = "relatorio_REFRESH_" + nome_arquivo_seguro(
                    refreshed_event.get("nome_empresa", "empresa")
                ).replace("relatorio_", "", 1)
                caminho_txt = salvar_relatorio_txt(
                    refreshed_event["relatorio_texto"],
                    nome_base=base_refresh,
                    pasta=storage_targets["outputs_txt_pasta"],
                )
                caminho_hist = append_event(
                    refreshed_event,
                    pasta=storage_targets["history_pasta"],
                    arquivo=storage_targets["history_arquivo"],
                )

                st.session_state["evento_aberto"] = refreshed_event
                st.session_state["carregado"] = refreshed_event
                st.session_state["ultimo_out"] = None

                st.success(f"Relatorio refresh salvo: {caminho_txt}")
                st.info(f"Evento de refresh append no historico: {caminho_hist}")
                st.rerun()

if demo_mode:
    st.warning("DEMO — não insira dados sensíveis.")

st.subheader("Dados da empresa")
col1, col2 = st.columns(2)
with col1:
    nome_empresa = st.text_input("Nome da empresa", value=nome_default)
with col2:
    receita_anual = st.number_input("Receita anual (R$)", min_value=0.0, value=receita_default, step=10000.0, format="%.2f")

periodicidades = ["mensal", "trimestral", "anual"]
periodicidade_index = periodicidades.index(periodicidade_default) if periodicidade_default in periodicidades else 2
periodicidade = st.selectbox("Periodicidade", periodicidades, index=periodicidade_index)
competencia_input = st.text_input(
    "Competencia",
    value=competencia_default,
    placeholder=_competencia_placeholder(periodicidade),
)

margem_lucro = None
tipo_atividade = None
rbt12 = None
receita_base_periodo = None
anexo_simples = None
fator_r = None
folha_12m = None

if regime == REGIME_DISPLAY_SIMPLES:
    rbt12 = st.number_input(
        "RBT12 (Receita Bruta acumulada 12 meses) (R$)",
        min_value=0.0,
        value=max(0.0, rbt12_default),
        step=10000.0,
        format="%.2f",
    )
    receita_base_periodo = st.number_input(
        "Receita base do cálculo (R$)",
        min_value=0.0,
        value=max(0.0, receita_base_default if receita_base_default > 0 else receita_anual),
        step=10000.0,
        format="%.2f",
        help="No MVP anual, use a receita anual informada.",
    )
    anexos = ["I", "II", "III", "IV", "V", "III/V"]
    idx_anexo = anexos.index(anexo_default) if anexo_default in anexos else 0
    anexo_simples = st.selectbox("Anexo do Simples", anexos, index=idx_anexo)

    if anexo_simples == "III/V":
        modo_fator_r = st.radio(
            "Entrada para Fator R",
            ["Informar fator_r", "Informar folha_12m"],
            horizontal=True,
        )
        if modo_fator_r == "Informar fator_r":
            fator_r = st.number_input(
                "fator_r (0 a 1)",
                min_value=0.0,
                max_value=1.0,
                value=min(1.0, max(0.0, fator_r_default)),
                step=0.01,
                format="%.4f",
            )
            folha_12m = None
        else:
            folha_12m = st.number_input(
                "folha_12m (R$)",
                min_value=0.0,
                value=max(0.0, folha_12m_default),
                step=1000.0,
                format="%.2f",
            )
            fator_r = None

elif regime == REGIME_DISPLAY_PRESUMIDO:
    atividades = ["Comercio", "Industria", "Servicos (geral)", "Outros"]
    idx_default = atividades.index(tipo_atividade_default) if tipo_atividade_default in atividades else 0
    tipo_atividade = st.selectbox(
        "Tipo de atividade (Presumido)",
        atividades,
        index=idx_default,
    )

elif regime == REGIME_DISPLAY_REAL:
    margem_txt = st.text_input(
        "Margem de lucro estimada (ex: 10%)",
        value=str(round(margem_default * 100, 2)).replace(".", ","),
    )
    margem_lucro = parse_percent(margem_txt)

st.markdown("---")
bg1, bg2 = st.columns(2)
with bg1:
    gerar = st.button("Gerar diagnostico", use_container_width=True)
with bg2:
    comparar_regimes = st.button("Comparar regimes", use_container_width=True)

if gerar or comparar_regimes:
    if not nome_empresa.strip():
        st.error("Informe o nome da empresa.")
        st.stop()
    if receita_anual <= 0:
        st.error("Informe a receita anual (> 0).")
        st.stop()

    if regime == REGIME_DISPLAY_SIMPLES:
        if rbt12 is None or float(rbt12) <= 0:
            st.error("Informe RBT12 maior que zero.")
            st.stop()
        if receita_base_periodo is None or float(receita_base_periodo) <= 0:
            st.error("Informe receita base do cálculo maior que zero.")
            st.stop()
        if anexo_simples not in ("I", "II", "III", "IV", "V", "III/V"):
            st.error("Informe um anexo válido do Simples.")
            st.stop()
        if anexo_simples == "III/V":
            if fator_r is None and folha_12m is None:
                st.error("Para anexo III/V, informe fator_r ou folha_12m.")
                st.stop()
            if fator_r is not None and not (0.0 <= float(fator_r) <= 1.0):
                st.error("fator_r deve estar entre 0 e 1.")
                st.stop()
            if folha_12m is not None and float(folha_12m) < 0:
                st.error("folha_12m deve ser maior ou igual a zero.")
                st.stop()

    periodicidade_norm = validar_periodicidade(periodicidade)
    competencia_ok, competencia_result = validar_competencia(periodicidade_norm, competencia_input)
    if not competencia_ok:
        st.error(competencia_result)
        st.stop()

    cenarios = {
        f"Otimista ({cen_otim}%)": parse_percent(cen_otim),
        f"Base ({cen_base}%)": parse_percent(cen_base),
        f"Pessimista ({cen_pess}%)": parse_percent(cen_pess),
    }

    regime_code = "SIMPLES" if regime == REGIME_DISPLAY_SIMPLES else ("PRESUMIDO" if regime == REGIME_DISPLAY_PRESUMIDO else "REAL")
    regime_model = "tabelado" if regime == REGIME_DISPLAY_SIMPLES else "padrao"

    inp = DiagnosticInput(
        nome_empresa=nome_empresa.strip(),
        receita_anual=float(receita_anual),
        regime=regime,
        regime_code=regime_code,
        regime_model=regime_model,
        margem_lucro=margem_lucro,
        tipo_atividade=tipo_atividade,
        rbt12=float(rbt12) if rbt12 is not None else None,
        receita_base_periodo=float(receita_base_periodo) if receita_base_periodo is not None else None,
        anexo_simples=anexo_simples,
        fator_r=float(fator_r) if fator_r is not None else None,
        folha_12m=float(folha_12m) if folha_12m is not None else None,
        periodicidade=periodicidade_norm,
        competencia=competencia_result,
        modo_analise=modo_analise,
        cenarios=cenarios,
    )

    out = service.run(inp)
    st.session_state["ultimo_out"] = out
    st.session_state["evento_aberto"] = None
    st.success("Diagnostico gerado.")

evento_exibicao: Optional[Dict[str, Any]] = None
origem_historico = False

if st.session_state["ultimo_out"] is not None:
    evento_exibicao = normalize_event(st.session_state["ultimo_out"].to_event())
else:
    evento_salvo = st.session_state["evento_aberto"]
    if evento_salvo:
        evento_exibicao = normalize_event(evento_salvo)
        origem_historico = True

if evento_exibicao:
    if origem_historico:
        st.caption("Visualizando analise salva no historico.")

    _renderizar_resultado(evento_exibicao)
    relatorio = get_event_report_text(evento_exibicao)

    st.subheader("Relatorio executivo")
    st.text_area("Conteudo", value=relatorio, height=380)

    st.subheader("Exportacao")
    base = nome_arquivo_seguro(evento_exibicao.get("nome_empresa", "empresa"))
    if origem_historico:
        base = base + "_historico_aberto"

    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("Salvar TXT"):
            caminho = salvar_relatorio_txt(
                relatorio,
                nome_base=base,
                pasta=storage_targets["outputs_txt_pasta"],
            )
            st.info(f"TXT salvo: {caminho}")

    with b2:
        if st.button("Salvar PDF"):
            caminho = salvar_relatorio_pdf(
                relatorio,
                nome_base=base,
                pasta=storage_targets["outputs_pdf_pasta"],
            )
            st.info(f"PDF salvo: {caminho}")

    with b3:
        if not origem_historico and st.button("Salvar no historico"):
            caminho = append_event(
                evento_exibicao,
                pasta=storage_targets["history_pasta"],
                arquivo=storage_targets["history_arquivo"],
            )
            st.info(f"Historico atualizado: {caminho}")
            st.rerun()
else:
    st.info("Gere um diagnostico ou abra uma analise salva para ver resultados.")
