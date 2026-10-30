"""Reportes y exportaciones."""
from __future__ import annotations

import csv
from pathlib import Path

from core.database import FJPP_Database
from modulos.certificados import ESTADOS


class FJPP_ServicioReportes:
    def __init__(self, db: FJPP_Database):
        self.db = db

    def FJPP_resumen(self) -> dict:
        def FJPP_contar(sql, params=()):
            return self.db.FJPP_consultar_uno(sql, params)["n"]

        facturado = self.db.FJPP_consultar_uno(
            "SELECT COALESCE(SUM(monto_centimos), 0) AS n FROM matriculas WHERE estado != 'RETIRADA'"
        )["n"]
        recaudado = self.db.FJPP_consultar_uno(
            "SELECT COALESCE(SUM(p.monto_centimos), 0) AS n FROM pagos p "
            "JOIN matriculas m ON m.id = p.matricula_id "
            "WHERE p.anulado = 0 AND m.estado != 'RETIRADA'"
        )["n"]
        return {
            "estudiantes_activos": FJPP_contar("SELECT COUNT(*) AS n FROM estudiantes WHERE activo = 1"),
            "cursos_activos": FJPP_contar("SELECT COUNT(*) AS n FROM cursos WHERE activo = 1"),
            "matriculas_en_curso": FJPP_contar("SELECT COUNT(*) AS n FROM matriculas WHERE estado = 'EN_CURSO'"),
            "facturado_centimos": facturado,
            "recaudado_centimos": recaudado,
            "por_cobrar_centimos": facturado - recaudado,
            "certificados": {
                estado: FJPP_contar("SELECT COUNT(*) AS n FROM certificados WHERE estado = ?", (estado,))
                for estado in ESTADOS
            },
        }


def FJPP_exportar_csv(filas: list[dict], columnas: list[str], ruta: str | Path) -> Path:
    """Escribe filas (lista de dicts) en CSV legible por Excel."""
    destino = Path(ruta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "w", newline="", encoding="utf-8-sig") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=columnas, extrasaction="ignore")
        escritor.writeheader()
        escritor.writerows(filas)
    return destino
