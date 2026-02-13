def escolher_regime() -> str:
    while True:
        print("\nEscolha o regime atual:")
        print("1) Simples Nacional")
        print("2) Lucro Presumido")
        print("3) Lucro Real")

        op = input("Opção: ").strip()
        if op in ("1", "2", "3"):
            return op

        print("Opção inválida. Tente novamente.")
