from __future__ import annotations

import os
import sys
from pathlib import Path

from streamlit.web import cli as stcli


def _app_path() -> Path:
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", None)
        if isinstance(base, str) and base:
            return Path(base) / "app.py"
        return Path(sys.executable).resolve().parent / "app.py"
    return Path(__file__).resolve().parent / "app.py"


def main() -> int:
    os.environ["TDE_DEMO"] = "1"
    app_script = _app_path()
    if not app_script.exists():
        print(f"Erro: app.py nao encontrado em: {app_script}")
        return 2

    print("Tax Diagnostic Engine - DEMO")
    print("Modo DEMO ativado (TDE_DEMO=1).")
    print("URL local esperada: http://localhost:8501")
    print("Para encerrar, pressione CTRL+C.")

    sys.argv = [
        "streamlit",
        "run",
        str(app_script),
        "--server.port",
        "8501",
        "--server.headless",
        "false",
        "--browser.gatherUsageStats",
        "false",
    ]
    stcli.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
