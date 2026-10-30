"""Configuración central del sistema.

Las rutas se calculan respecto a la carpeta del programa. Cuando el sistema
se empaquete con PyInstaller (sys.frozen), la carpeta será la del .exe, de modo
que la base de datos y los PDF queden junto al ejecutable y no dentro del
paquete temporal.
"""
from __future__ import annotations

import sys
from pathlib import Path


def _FJPP_carpeta_base() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


BASE_DIR = _FJPP_carpeta_base()
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "academico.db"
CERT_DIR = DATA_DIR / "certificados_firmados"   # PDF firmados recibidos
SOLICITUDES_DIR = DATA_DIR / "lotes_envio"      # CSV enviados a la oficina que firma

MONEDA = "S/"

# Si es True, solo se puede solicitar el certificado cuando el estudiante
# no tiene saldo pendiente en esa matrícula.
EXIGIR_PAGO_COMPLETO = True

METODOS_PAGO = ("EFECTIVO", "TRANSFERENCIA", "DEPOSITO", "YAPE/PLIN", "OTRO")


def FJPP_asegurar_directorios() -> None:
    for carpeta in (DATA_DIR, CERT_DIR, SOLICITUDES_DIR):
        carpeta.mkdir(parents=True, exist_ok=True)
