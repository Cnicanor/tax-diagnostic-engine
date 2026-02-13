import re
from datetime import datetime

from dto import DiagnosticInput
from file_exporter import salvar_relatorio_txt
from formatters import formatar_reais
from history_store import append_event, list_events
from input_utils import validar_competencia, validar_periodicidade
from outputs_manager import listar_relatorios, ler_relatorio
from pdf_exporter import salvar_relatorio_pdf
from regime_selector import escolher_regime
from tax_engine import DiagnosticService


def nome_arquivo_seguro(nome_empresa: str) -> str:
    nome_limpo = re.sub(r"[^a-zA-Z0-9_ -]", "", nome_empresa)
    nome_limpo = nome_limpo.strip().replace(" ", "_")
    return f"relatorio_{nome_limpo or 'empresa'}"


def _competencia_padrao(periodicidade: str) -> str:
    agora = datetime.now()
    p = validar_periodicidade(periodicidade)
    if p == "mensal":
        return agora.strftime("%Y-%m")
    if p == "trimestral":
        trimestre = ((agora.month - 1) // 3) + 1
        return f"{agora.year}-T{trimestre}"
    return agora.strftime("%Y")


def ler_periodicidade_competencia() -> tuple[str, str]:
    print("\nPeriodicidade de apuracao:")
    print("1) mensal")
    print("2) trimestral")
    print("3) anual")

    mapa_periodicidade = {
        "1": "mensal",
        "2": "trimestral",
        "3": "anual",
    }

    while True:
        op = input("Opcao: ").strip()
        if op in mapa_periodicidade:
            periodicidade = validar_periodicidade(mapa_periodicidade[op])
            break
        print("Opcao invalida. Tente novamente.")

    while True:
        padrao = _competencia_padrao(periodicidade)
        if periodicidade == "mensal":
            prompt = f"Competencia mensal (YYYY-MM) [ENTER para {padrao}]: "
        elif periodicidade == "trimestral":
            prompt = f"Competencia trimestral (YYYY-Tn) [ENTER para {padrao}]: "
        else:
            prompt = f"Competencia anual (YYYY) [ENTER para {padrao}]: "

        comp_raw = input(prompt).strip()
        competencia = comp_raw if comp_raw else padrao
        ok, valor = validar_competencia(periodicidade, competencia)
        if ok:
            return periodicidade, valor
        print(valor)


def ler_modo_analise() -> str:
    print("\nModo de recomendação:")
    print("1) Conservador")
    print("2) Estratégico")
    while True:
        op = input("Opcao: ").strip()
        if op == "1":
            return "conservador"
        if op == "2":
            return "estrategico"
        print("Opcao invalida. Tente novamente.")


def _ler_float(prompt: str, default: float | None = None) -> float:
    while True:
        raw = input(prompt).strip().replace(",", ".")
        if raw == "" and default is not None:
            return default
        try:
            return float(raw)
        except ValueError:
            print("Valor invalido. Tente novamente.")


def _ler_simples_tabelado_inputs(receita_anual: float) -> tuple[float, float, str, float | None, float | None]:
    rbt12 = _ler_float(
        f"RBT12 (ENTER para usar receita anual = {receita_anual:.2f}): ",
        default=receita_anual,
    )
    while rbt12 <= 0:
        print("RBT12 deve ser maior que zero.")
        rbt12 = _ler_float("RBT12: ")

    receita_base = _ler_float(
        f"Receita base do calculo (ENTER para usar receita anual = {receita_anual:.2f}): ",
        default=receita_anual,
    )
    while receita_base <= 0:
        print("Receita base deve ser maior que zero.")
        receita_base = _ler_float("Receita base do calculo: ")

    print("\nAnexo do Simples:")
    print("1) I")
    print("2) II")
    print("3) III")
    print("4) IV")
    print("5) V")
    print("6) III-V (com Fator R)")
    mapa_anexo = {"1": "I", "2": "II", "3": "III", "4": "IV", "5": "V", "6": "III/V"}
    while True:
        op = input("Opcao: ").strip()
        if op in mapa_anexo:
            anexo = mapa_anexo[op]
            break
        print("Opcao invalida. Tente novamente.")

    fator_r: float | None = None
    folha_12m: float | None = None
    if anexo == "III/V":
        print("\nFator R para servicos (III/V):")
        print("1) Informar fator_r diretamente (0 a 1)")
        print("2) Informar folha_12m (fator_r = folha_12m / RBT12)")
        while True:
            op_fr = input("Opcao: ").strip()
            if op_fr == "1":
                fator_r = _ler_float("fator_r (0 a 1): ")
                if 0 <= fator_r <= 1:
                    break
                print("fator_r deve estar entre 0 e 1.")
                fator_r = None
                continue
            if op_fr == "2":
                folha_12m = _ler_float("folha_12m (>= 0): ")
                if folha_12m >= 0:
                    break
                print("folha_12m deve ser >= 0.")
                folha_12m = None
                continue
            print("Opcao invalida. Tente novamente.")

    return receita_base, rbt12, anexo, fator_r, folha_12m


service = DiagnosticService()


def executar_analise():
    print("\n=== NOVA ANALISE ===")

    nome_empresa = input("Digite o nome da empresa: ").strip()

    while True:
        try:
            receita_anual = float(input("Digite a receita anual da empresa: "))
            if receita_anual <= 0:
                print("A receita deve ser maior que zero.")
                continue
            break
        except ValueError:
            print("Valor invalido. Ex: 500000")

    regime_op = escolher_regime()
    periodicidade, competencia = ler_periodicidade_competencia()
    modo_analise = ler_modo_analise()

    if regime_op == "1":
        regime = "Simples Nacional"
        receita_base, rbt12, anexo, fator_r, folha_12m = _ler_simples_tabelado_inputs(receita_anual)
        inp = DiagnosticInput(
            nome_empresa=nome_empresa,
            receita_anual=receita_anual,
            regime=regime,
            regime_code="SIMPLES",
            regime_model="tabelado",
            rbt12=rbt12,
            receita_base_periodo=receita_base,
            anexo_simples=anexo,
            fator_r=fator_r,
            folha_12m=folha_12m,
            periodicidade=periodicidade,
            competencia=competencia,
            modo_analise=modo_analise,
        )

    elif regime_op == "2":
        regime = "Lucro Presumido"
        print("\nTipo de atividade (Presumido):")
        print("1) Comercio")
        print("2) Industria")
        print("3) Servicos (geral)")
        print("4) Outros")
        while True:
            atividade_op = input("Opcao: ").strip()
            mapa_atividade = {
                "1": "Comercio",
                "2": "Industria",
                "3": "Servicos (geral)",
                "4": "Outros",
            }
            if atividade_op in mapa_atividade:
                tipo_atividade = mapa_atividade[atividade_op]
                break
            print("Opcao invalida. Tente novamente.")
        inp = DiagnosticInput(
            nome_empresa=nome_empresa,
            receita_anual=receita_anual,
            regime=regime,
            regime_code="PRESUMIDO",
            regime_model="padrao",
            tipo_atividade=tipo_atividade,
            periodicidade=periodicidade,
            competencia=competencia,
            modo_analise=modo_analise,
        )

    else:
        regime = "Lucro Real"
        while True:
            try:
                margem = float(input("Digite a margem estimada (ex: 10 para 10%): ").strip().replace(",", "."))
                if margem > 1:
                    margem = margem / 100
                if margem < 0:
                    print("Margem nao pode ser negativa.")
                    continue
                break
            except ValueError:
                print("Entrada invalida. Ex: 10 ou 0.10")
        inp = DiagnosticInput(
            nome_empresa=nome_empresa,
            receita_anual=receita_anual,
            regime=regime,
            regime_code="REAL",
            regime_model="padrao",
            margem_lucro=margem,
            periodicidade=periodicidade,
            competencia=competencia,
            modo_analise=modo_analise,
        )

    out = service.run(inp)

    print("\nRegime:", out.regime)
    print("Imposto atual:", formatar_reais(out.imposto_atual))
    print("\n" + out.relatorio_texto)

    base = nome_arquivo_seguro(out.nome_empresa)
    caminho_txt = salvar_relatorio_txt(out.relatorio_texto, nome_base=base)
    print("\nTXT gerado:", caminho_txt)

    caminho_hist = append_event(out.to_event())
    print("Historico atualizado:", caminho_hist)


def mostrar_relatorios():
    relatorios = listar_relatorios()
    if not relatorios:
        print("Nenhum relatorio encontrado em outputs.")
        return []
    print("\nRelatorios (mais recentes primeiro):")
    for i, nome in enumerate(relatorios, start=1):
        print(f"{i}. {nome}")
    return relatorios


def abrir_relatorio():
    relatorios = mostrar_relatorios()
    if not relatorios:
        return

    escolha = input("\nNumero do relatorio para abrir (ENTER cancela): ").strip()
    if escolha == "":
        return
    if not escolha.isdigit():
        print("Digite um numero valido.")
        return

    idx = int(escolha)
    if idx < 1 or idx > len(relatorios):
        print("Fora do intervalo.")
        return

    nome_arquivo = relatorios[idx - 1]
    conteudo = ler_relatorio(nome_arquivo)
    if conteudo is None:
        print("Falha ao ler arquivo.")
        return

    print("\n================ RELATORIO ================")
    print(f"Arquivo: {nome_arquivo}")
    print("===========================================")
    print(conteudo)
    print("===========================================")


def exportar_relatorio_pdf():
    relatorios = mostrar_relatorios()
    if not relatorios:
        return

    escolha = input("\nNumero do relatorio para PDF (ENTER cancela): ").strip()
    if escolha == "":
        return
    if not escolha.isdigit():
        print("Digite um numero valido.")
        return

    idx = int(escolha)
    if idx < 1 or idx > len(relatorios):
        print("Fora do intervalo.")
        return

    nome_arquivo_txt = relatorios[idx - 1]
    conteudo = ler_relatorio(nome_arquivo_txt)
    if conteudo is None:
        print("Falha ao ler TXT.")
        return

    base_pdf = nome_arquivo_txt.replace(".txt", "")
    caminho_pdf = salvar_relatorio_pdf(conteudo, nome_base=base_pdf, pasta="outputs_pdfs")
    print("PDF gerado:", caminho_pdf)


def ver_historico():
    eventos = list_events(limit=20)
    if not eventos:
        print("Historico vazio.")
        return

    print("\n=== HISTORICO (ultimos 20) ===")
    for i, e in enumerate(eventos, start=1):
        print(f"\n#{i} - {e.get('timestamp')}")
        print("Empresa:", e.get("nome_empresa"))
        print("Receita:", formatar_reais(e.get("receita_anual", 0)))
        print("Regime:", e.get("regime"))
        print("Imposto atual:", formatar_reais(e.get("imposto_atual", 0)))


def menu():
    opcoes = {
        "1": ("Nova analise", executar_analise),
        "3": ("Listar relatorios TXT", mostrar_relatorios),
        "4": ("Abrir relatorio TXT", abrir_relatorio),
        "5": ("Exportar TXT para PDF", exportar_relatorio_pdf),
        "6": ("Ver historico", ver_historico),
    }

    while True:
        print("\n===================================")
        print("TAX DIAGNOSTIC ENGINE - MENU")
        print("===================================")
        for k, (desc, _) in opcoes.items():
            print(f"{k}) {desc}")
        print("2) Sair")

        op = input("Escolha uma opcao: ").strip()
        if op == "2":
            print("Saindo...")
            break
        if op in opcoes:
            opcoes[op][1]()
        else:
            print("Opcao invalida.")


if __name__ == "__main__":
    menu()
