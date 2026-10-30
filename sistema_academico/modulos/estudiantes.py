"""Módulo de estudiantes."""
from __future__ import annotations

import sqlite3

from core.database import FJPP_Database
from core.excepciones import FJPP_ErrorDeNegocio, FJPP_NoEncontrado, FJPP_ValidacionError
from core.validadores import FJPP_requerido, FJPP_validar_dni, FJPP_validar_email, FJPP_validar_telefono

CAMPOS_EDITABLES = {"nombres", "apellidos", "email", "telefono"}


class FJPP_ServicioEstudiantes:
    def __init__(self, db: FJPP_Database):
        self.db = db

    def FJPP_crear(self, dni, nombres, apellidos, email="", telefono="") -> int:
        dni = FJPP_validar_dni(dni)
        datos = (
            dni,
            FJPP_requerido(nombres, "Los nombres"),
            FJPP_requerido(apellidos, "Los apellidos"),
            FJPP_validar_email(email),
            FJPP_validar_telefono(telefono),
        )
        try:
            with self.db.FJPP_transaccion() as c:
                cur = c.execute(
                    "INSERT INTO estudiantes (dni, nombres, apellidos, email, telefono) "
                    "VALUES (?, ?, ?, ?, ?)",
                    datos,
                )
                return cur.lastrowid
        except sqlite3.IntegrityError:
            raise FJPP_ErrorDeNegocio(f"Ya existe un estudiante con DNI {dni}.") from None

    def FJPP_obtener(self, estudiante_id: int) -> dict:
        fila = self.db.FJPP_consultar_uno("SELECT * FROM estudiantes WHERE id = ?", (estudiante_id,))
        if fila is None:
            raise FJPP_NoEncontrado(f"No existe el estudiante con id {estudiante_id}.")
        return dict(fila)

    def FJPP_obtener_por_dni(self, dni: str) -> dict:
        dni = FJPP_validar_dni(dni)
        fila = self.db.FJPP_consultar_uno("SELECT * FROM estudiantes WHERE dni = ?", (dni,))
        if fila is None:
            raise FJPP_NoEncontrado(f"No existe un estudiante con DNI {dni}.")
        return dict(fila)

    def FJPP_buscar(self, texto: str = "", solo_activos: bool = True) -> list[dict]:
        patron = f"%{texto.strip()}%"
        sql = (
            "SELECT * FROM estudiantes "
            "WHERE (dni LIKE ? OR nombres LIKE ? OR apellidos LIKE ?) "
        )
        if solo_activos:
            sql += "AND activo = 1 "
        sql += "ORDER BY apellidos, nombres"
        return [dict(f) for f in self.db.FJPP_consultar(sql, (patron, patron, patron))]

    def FJPP_actualizar(self, estudiante_id: int, **campos) -> None:
        self.FJPP_obtener(estudiante_id)
        cambios = {}
        for clave, valor in campos.items():
            if clave not in CAMPOS_EDITABLES:
                raise FJPP_ValidacionError(f"El campo '{clave}' no se puede editar.")
            if clave == "email":
                cambios[clave] = FJPP_validar_email(valor)
            elif clave == "telefono":
                cambios[clave] = FJPP_validar_telefono(valor)
            else:
                cambios[clave] = FJPP_requerido(valor, clave.capitalize())
        if not cambios:
            return
        # Las claves salen de la lista blanca CAMPOS_EDITABLES, no del usuario.
        asignaciones = ", ".join(f"{clave} = ?" for clave in cambios)
        with self.db.FJPP_transaccion() as c:
            c.execute(
                f"UPDATE estudiantes SET {asignaciones} WHERE id = ?",
                (*cambios.values(), estudiante_id),
            )

    def FJPP_desactivar(self, estudiante_id: int) -> None:
        self.FJPP_obtener(estudiante_id)
        en_curso = self.db.FJPP_consultar_uno(
            "SELECT COUNT(*) AS n FROM matriculas WHERE estudiante_id = ? AND estado = 'EN_CURSO'",
            (estudiante_id,),
        )["n"]
        if en_curso:
            raise FJPP_ErrorDeNegocio(
                f"El estudiante tiene {en_curso} matrícula(s) en curso; "
                "complételas o retírelas antes de desactivarlo."
            )
        with self.db.FJPP_transaccion() as c:
            c.execute("UPDATE estudiantes SET activo = 0 WHERE id = ?", (estudiante_id,))
