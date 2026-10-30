"""Punto de entrada del sistema.

    python main.py          # inicia el sistema
    python main.py --demo   # carga datos de ejemplo si la base está vacía
"""
from __future__ import annotations

import argparse

import config
from contexto import FJPP_Contexto
from core.database import FJPP_Database
from demo import FJPP_cargar_demo
from ui.menus import FJPP_Aplicacion


def FJPP_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sistema académico: pagos, cursos y certificados")
    parser.add_argument("--demo", action="store_true", help="cargar datos de ejemplo (base vacía)")
    args = parser.parse_args(argv)

    config.FJPP_asegurar_directorios()
    db = FJPP_Database(config.DB_PATH)
    try:
        ctx = FJPP_Contexto(db)
        if args.demo:
            if FJPP_cargar_demo(ctx):
                print("Datos de ejemplo cargados.")
            else:
                print("La base ya tiene datos; no se cargó la demo.")
        FJPP_Aplicacion(ctx).FJPP_ejecutar()
    except (KeyboardInterrupt, EOFError):
        print("\n\nSesión terminada.")
    finally:
        db.FJPP_cerrar()
    return 0


if __name__ == "__main__":
    raise SystemExit(FJPP_main())
