from typing import List, Dict, Any

from formatters import formatar_reais


def montar_relatorio_executivo(
    nome_empresa: str,
    receita_anual: float,
    aliquota_atual: float,
    imposto_atual: float,
    resultados: List[Dict[str, Any]],
) -> str:
    linhas = []
    linhas.append("==============================================")
    linhas.append("         RELATÓRIO - TAX DIAGNOSTIC ENGINE    ")
    linhas.append("==============================================")
    linhas.append(f"Empresa: {nome_empresa}")
    linhas.append(f"Receita anual informada: {formatar_reais(receita_anual)}")
    linhas.append(f"Imposto atual estimado: {formatar_reais(imposto_atual)}")
    linhas.append("")

    linhas.append("=== RESULTADOS POR CENÁRIO (PÓS-REFORMA) ===")
    for r in resultados:
        linhas.append("")
        linhas.append(f"--- {r['nome_cenario']} ---")
        linhas.append(f"Alíquota: {r['aliquota_reforma']}")
        linhas.append(f"Imposto pós-reforma: {formatar_reais(r['imposto_reforma'])}")
        linhas.append(f"Diferença de impacto: {formatar_reais(r['diferenca'])}")
        linhas.append(f"Impacto percentual: {round(r['impacto_percentual'], 2)} %")
        linhas.append(f"Classificação: {r['classificacao']}")
        linhas.append(f"Recomendação: {r['recomendacao']}")

    linhas.append("")
    linhas.append("Observação: Simulação simplificada para diagnóstico inicial.")
    linhas.append("==============================================")
    return "\n".join(linhas)
