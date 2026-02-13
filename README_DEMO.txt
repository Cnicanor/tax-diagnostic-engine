TAX DIAGNOSTIC ENGINE - DEMO (Windows)

1) COMO BUILDAR O EXECUTAVEL
- Abra um terminal na pasta do projeto.
- Execute:
  BUILD_DEMO.bat

O script faz:
- cria .venv (se nao existir)
- instala requirements + pyinstaller
- gera o executavel onefile com rulesets incluidos

2) ONDE O EXE E GERADO
- dist\TaxDiagnosticDemo.exe

3) COMO EXECUTAR A DEMO
- Duplo clique em dist\TaxDiagnosticDemo.exe
  ou
- No terminal:
  dist\TaxDiagnosticDemo.exe

O launcher ativa automaticamente:
- TDE_DEMO=1
- Streamlit na porta 8501
- URL esperada: http://localhost:8501

4) ROTEIRO DE TESTE (60 SEGUNDOS)
1. Abra a DEMO e confirme aviso: "DEMO — nao insira dados sensiveis".
2. No sidebar, ative "Modo DEMO" (se ainda nao estiver ativo).
3. Clique em "Carregar Exemplo - Simples Nacional".
4. Clique em "Gerar diagnostico".
5. Clique em "Salvar no historico".
6. Valide criacao de arquivos/pastas:
   - data_demo\history.jsonl
   - outputs_demo\
   - outputs_demo_pdfs\

5) AVISOS E LIMITACOES
- Esta versao e para demonstracao.
- Nao inserir dados sensiveis.
- O motor produz estimativas e simplificacoes de diagnostico.
- A matematica tributaria nao foi alterada nesta etapa.
