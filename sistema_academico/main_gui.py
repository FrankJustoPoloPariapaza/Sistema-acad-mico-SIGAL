"""Punto de entrada de la versión con interfaz gráfica.

    python main_gui.py          # inicia la ventana
    python main_gui.py --demo   # carga datos de ejemplo si la base está vacía
"""
from __future__ import annotations

import argparse

import config
from contexto import FJPP_Contexto
from core.database import FJPP_Database
from demo import FJPP_cargar_demo


def FJPP_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sistema académico (interfaz gráfica)")
    parser.add_argument("--demo", action="store_true", help="cargar datos de ejemplo (base vacía)")
    args = parser.parse_args(argv)

    config.FJPP_asegurar_directorios()
    db = FJPP_Database(config.DB_PATH)
    try:
        ctx = FJPP_Contexto(db)
        if args.demo:
            FJPP_cargar_demo(ctx)
        from ui.gui.ventana import FJPP_lanzar  # import tardío: la consola no necesita Tkinter
        FJPP_lanzar(ctx)
    finally:
        db.FJPP_cerrar()
    return 0


if __name__ == "__main__":
    raise SystemExit(FJPP_main())
