"""Módulo de matrículas: qué cursos sigue cada estudiante y su deuda."""
from __future__ import annotations

import sqlite3

from core.database import FJPP_Database
from core.dinero import FJPP_a_centimos
from core.excepciones import FJPP_ErrorDeNegocio, FJPP_NoEncontrado
from core.validadores import FJPP_hoy_iso, FJPP_validar_fecha
from modulos.cursos import FJPP_ServicioCursos
from modulos.estudiantes import FJPP_ServicioEstudiantes

EN_CURSO, COMPLETADA, RETIRADA = "EN_CURSO", "COMPLETADA", "RETIRADA"

_SQL_DETALLE = """
SELECT m.id, m.estudiante_id, m.curso_id, m.fecha, m.estado, m.monto_centimos,
       e.dni, e.nombres || ' ' || e.apellidos AS estudiante,
       c.codigo AS curso_codigo, c.nombre AS curso, c.horas,
       COALESCE((SELECT SUM(p.monto_centimos) FROM pagos p
                 WHERE p.matricula_id = m.id AND p.anulado = 0), 0) AS pagado_centimos
FROM matriculas m
JOIN estudiantes e ON e.id = m.estudiante_id
JOIN cursos c ON c.id = m.curso_id
"""


def _FJPP_con_saldo(fila: sqlite3.Row) -> dict:
    datos = dict(fila)
    datos["saldo_centimos"] = datos["monto_centimos"] - datos["pagado_centimos"]
    return datos


class FJPP_ServicioMatriculas:
    def __init__(self, db: FJPP_Database, estudiantes: FJPP_ServicioEstudiantes, cursos: FJPP_ServicioCursos):
        self.db = db
        self.estudiantes = estudiantes
        self.cursos = cursos

    def FJPP_matricular(self, estudiante_id: int, curso_id: int, monto=None, fecha=None) -> int:
        estudiante = self.estudiantes.FJPP_obtener(estudiante_id)
        curso = self.cursos.FJPP_obtener(curso_id)
        if not estudiante["activo"]:
            raise FJPP_ErrorDeNegocio("El estudiante está inactivo.")
        if not curso["activo"]:
            raise FJPP_ErrorDeNegocio("El curso está inactivo y no admite matrículas.")
        centimos = curso["precio_centimos"] if monto in (None, "") else FJPP_a_centimos(monto)
        fecha_iso = FJPP_hoy_iso() if not fecha else FJPP_validar_fecha(fecha)
        try:
            with self.db.FJPP_transaccion() as c:
                cur = c.execute(
                    "INSERT INTO matriculas (estudiante_id, curso_id, fecha, monto_centimos) "
                    "VALUES (?, ?, ?, ?)",
                    (estudiante_id, curso_id, fecha_iso, centimos),
                )
                return cur.lastrowid
        except sqlite3.IntegrityError:
            raise FJPP_ErrorDeNegocio("El estudiante ya está matriculado en ese curso.") from None

    def FJPP_detalle(self, matricula_id: int) -> dict:
        fila = self.db.FJPP_consultar_uno(_SQL_DETALLE + "WHERE m.id = ?", (matricula_id,))
        if fila is None:
            raise FJPP_NoEncontrado(f"No existe la matrícula con id {matricula_id}.")
        return _FJPP_con_saldo(fila)

    def FJPP_listar_por_estudiante(self, estudiante_id: int) -> list[dict]:
        filas = self.db.FJPP_consultar(
            _SQL_DETALLE + "WHERE m.estudiante_id = ? ORDER BY m.fecha, m.id", (estudiante_id,)
        )
        return [_FJPP_con_saldo(f) for f in filas]

    def FJPP_listar_por_curso(self, curso_id: int) -> list[dict]:
        filas = self.db.FJPP_consultar(
            _SQL_DETALLE + "WHERE m.curso_id = ? ORDER BY e.apellidos, e.nombres", (curso_id,)
        )
        return [_FJPP_con_saldo(f) for f in filas]

    def FJPP_cambiar_estado(self, matricula_id: int, nuevo_estado: str) -> None:
        if nuevo_estado not in (COMPLETADA, RETIRADA):
            raise FJPP_ErrorDeNegocio("Solo se puede pasar a COMPLETADA o RETIRADA.")
        actual = self.FJPP_detalle(matricula_id)["estado"]
        if actual != EN_CURSO:
            raise FJPP_ErrorDeNegocio(f"La matrícula está {actual} y ya no puede cambiar de estado.")
        with self.db.FJPP_transaccion() as c:
            c.execute("UPDATE matriculas SET estado = ? WHERE id = ?", (nuevo_estado, matricula_id))
