"""Utilidades de entrada/salida por consola."""
from __future__ import annotations

from typing import Callable

from core.excepciones import FJPP_ErrorDeNegocio


def titulo(texto: str) -> None:
    print("\n" + "=" * 64)
    print(f" {texto}")
    print("=" * 64)


def FJPP_pedir(etiqueta: str, defecto: str | None = None, obligatorio: bool = True) -> str:
    while True:
        sufijo = f" [{defecto}]" if defecto not in (None, "") else ""
        valor = input(f"{etiqueta}{sufijo}: ").strip()
        if not valor and defecto is not None:
            return str(defecto)
        if valor or not obligatorio:
            return valor
        print("  Este dato es obligatorio.")


def FJPP_pedir_entero(etiqueta: str) -> int:
    while True:
        valor = FJPP_pedir(etiqueta)
        try:
            return int(valor)
        except ValueError:
            print("  Ingrese un número entero.")


def FJPP_confirmar(pregunta: str) -> bool:
    return input(f"{pregunta} (s/n): ").strip().lower() in ("s", "si", "sí", "y")


def FJPP_pausa() -> None:
    input("\nPresione Enter para continuar...")


def FJPP_tabla(filas: list[dict], columnas: list[tuple[str, str]], ancho_max: int = 38) -> None:
    """Imprime filas (dicts) como tabla. `columnas` = [(encabezado, clave), ...]."""
    if not filas:
        print("  (sin resultados)")
        return
    celdas = [
        [str(fila.get(clave, ""))[:ancho_max] for _, clave in columnas] for fila in filas
    ]
    anchos = [
        max(len(titulo_col), *(len(f[i]) for f in celdas))
        for i, (titulo_col, _) in enumerate(columnas)
    ]
    linea = "  ".join("-" * a for a in anchos)
    print("  ".join(t.ljust(a) for (t, _), a in zip(columnas, anchos)))
    print(linea)
    for fila in celdas:
        print("  ".join(valor.ljust(a) for valor, a in zip(fila, anchos)))


def FJPP_menu(titulo_menu: str, opciones: list[tuple[str, Callable[[], None]]],
         salida: str = "Volver") -> None:
    """Muestra un menú numerado hasta que el usuario elige 0."""
    while True:
        titulo(titulo_menu)
        for numero, (texto, _) in enumerate(opciones, start=1):
            print(f"  {numero}. {texto}")
        print(f"  0. {salida}")
        eleccion = input("\nOpción: ").strip()
        if eleccion == "0":
            return
        if not eleccion.isdigit() or not 1 <= int(eleccion) <= len(opciones):
            print("  Opción no válida.")
            continue
        try:
            opciones[int(eleccion) - 1][1]()
        except FJPP_ErrorDeNegocio as error:
            print(f"\n  [!] {error}")
        FJPP_pausa()
