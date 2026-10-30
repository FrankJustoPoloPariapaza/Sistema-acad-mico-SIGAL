"""Módulo de cursos."""
from __future__ import annotations

import sqlite3

from core.database import FJPP_Database
from core.dinero import FJPP_a_centimos
from core.excepciones import FJPP_ErrorDeNegocio, FJPP_NoEncontrado
from core.validadores import FJPP_entero_positivo, FJPP_requerido


class FJPP_ServicioCursos:
    def __init__(self, db: FJPP_Database):
        self.db = db

    def FJPP_crear(self, codigo, nombre, horas, precio) -> int:
        codigo = FJPP_requerido(codigo, "El código").upper()
        datos = (
            codigo,
            FJPP_requerido(nombre, "El nombre"),
            FJPP_entero_positivo(horas, "Las horas"),
            FJPP_a_centimos(precio),
        )
        try:
            with self.db.FJPP_transaccion() as c:
                cur = c.execute(
                    "INSERT INTO cursos (codigo, nombre, horas, precio_centimos) "
                    "VALUES (?, ?, ?, ?)",
                    datos,
                )
                return cur.lastrowid
        except sqlite3.IntegrityError:
            raise FJPP_ErrorDeNegocio(f"Ya existe un curso con código {codigo}.") from None

    def FJPP_obtener(self, curso_id: int) -> dict:
        fila = self.db.FJPP_consultar_uno("SELECT * FROM cursos WHERE id = ?", (curso_id,))
        if fila is None:
            raise FJPP_NoEncontrado(f"No existe el curso con id {curso_id}.")
        return dict(fila)

    def FJPP_obtener_por_codigo(self, codigo: str) -> dict:
        codigo = FJPP_requerido(codigo, "El código").upper()
        fila = self.db.FJPP_consultar_uno("SELECT * FROM cursos WHERE codigo = ?", (codigo,))
        if fila is None:
            raise FJPP_NoEncontrado(f"No existe el curso con código {codigo}.")
        return dict(fila)

    def FJPP_listar(self, solo_activos: bool = True) -> list[dict]:
        sql = "SELECT * FROM cursos "
        if solo_activos:
            sql += "WHERE activo = 1 "
        sql += "ORDER BY codigo"
        return [dict(f) for f in self.db.FJPP_consultar(sql)]

    def FJPP_cambiar_precio(self, curso_id: int, nuevo_precio) -> None:
        """El nuevo precio no afecta a matrículas ya registradas (conservan su monto)."""
        self.FJPP_obtener(curso_id)
        centimos = FJPP_a_centimos(nuevo_precio)
        with self.db.FJPP_transaccion() as c:
            c.execute("UPDATE cursos SET precio_centimos = ? WHERE id = ?", (centimos, curso_id))

    def FJPP_desactivar(self, curso_id: int) -> None:
        """Un curso inactivo no admite nuevas matrículas; el historial se conserva."""
        self.FJPP_obtener(curso_id)
        with self.db.FJPP_transaccion() as c:
            c.execute("UPDATE cursos SET activo = 0 WHERE id = ?", (curso_id,))
