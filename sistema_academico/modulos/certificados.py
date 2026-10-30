"""Módulo de certificados.

Flujo:
  1. Se solicita el certificado de una matrícula COMPLETADA (y pagada).   -> PENDIENTE_FIRMA
  2. Se genera un lote (CSV) para enviarlo a la oficina que firma.          -> ENVIADO_A_FIRMA
  3. La oficina devuelve el PDF ya firmado; se importa y se registra.       -> FIRMADO

El PDF recibido se copia tal cual (sin reescribirlo, para no invalidar la firma)
y se guarda su huella SHA-256 para detectar alteraciones posteriores.
"""
from __future__ import annotations

import csv
import hashlib
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

import config
from core.database import FJPP_Database
from core.dinero import FJPP_formatear
from core.excepciones import FJPP_ErrorDeNegocio, FJPP_NoEncontrado
from core.validadores import FJPP_requerido
from modulos import firma_digital
from modulos.matriculas import COMPLETADA, FJPP_ServicioMatriculas

PENDIENTE, ENVIADO, FIRMADO = "PENDIENTE_FIRMA", "ENVIADO_A_FIRMA", "FIRMADO"
ESTADOS = (PENDIENTE, ENVIADO, FIRMADO)

_SQL_LISTA = """
SELECT ce.id, ce.matricula_id, ce.codigo, ce.estado, ce.fecha_solicitud, ce.fecha_envio,
       ce.fecha_firmado, ce.archivo_pdf, ce.sha256, ce.firmas_detectadas, ce.verificacion,
       e.dni, e.nombres || ' ' || e.apellidos AS estudiante,
       c.codigo AS curso_codigo, c.nombre AS curso, c.horas
FROM certificados ce
JOIN matriculas m ON m.id = ce.matricula_id
JOIN estudiantes e ON e.id = m.estudiante_id
JOIN cursos c ON c.id = m.curso_id
"""


class FJPP_ServicioCertificados:
    def __init__(self, db: FJPP_Database, matriculas: FJPP_ServicioMatriculas,
                 dir_certificados: Path | None = None, dir_solicitudes: Path | None = None):
        self.db = db
        self.matriculas = matriculas
        self.dir_certificados = Path(dir_certificados or config.CERT_DIR)
        self.dir_solicitudes = Path(dir_solicitudes or config.SOLICITUDES_DIR)

    # ------------------------------------------------------------------ consulta
    def FJPP_obtener(self, codigo: str) -> dict:
        codigo = FJPP_requerido(codigo, "El código del certificado").upper()
        fila = self.db.FJPP_consultar_uno(_SQL_LISTA + "WHERE ce.codigo = ?", (codigo,))
        if fila is None:
            raise FJPP_NoEncontrado(f"No existe el certificado {codigo}.")
        return dict(fila)

    def FJPP_listar(self, estado: str | None = None) -> list[dict]:
        if estado is None:
            filas = self.db.FJPP_consultar(_SQL_LISTA + "ORDER BY ce.id")
        else:
            if estado not in ESTADOS:
                raise FJPP_ErrorDeNegocio(f"Estado inválido. Use: {', '.join(ESTADOS)}.")
            filas = self.db.FJPP_consultar(_SQL_LISTA + "WHERE ce.estado = ? ORDER BY ce.id", (estado,))
        return [dict(f) for f in filas]

    def FJPP_listar_por_estudiante(self, estudiante_id: int) -> list[dict]:
        filas = self.db.FJPP_consultar(
            _SQL_LISTA + "WHERE m.estudiante_id = ? ORDER BY ce.id", (estudiante_id,)
        )
        return [dict(f) for f in filas]

    # ------------------------------------------------------------------ paso 1
    def FJPP_solicitar(self, matricula_id: int) -> dict:
        matricula = self.matriculas.FJPP_detalle(matricula_id)
        if matricula["estado"] != COMPLETADA:
            raise FJPP_ErrorDeNegocio(
                "La matrícula debe estar COMPLETADA para solicitar el certificado."
            )
        if config.EXIGIR_PAGO_COMPLETO and matricula["saldo_centimos"] > 0:
            raise FJPP_ErrorDeNegocio(
                f"El estudiante tiene un saldo pendiente de "
                f"{FJPP_formatear(matricula['saldo_centimos'])}."
            )
        try:
            with self.db.FJPP_transaccion() as c:
                cur = c.execute(
                    "INSERT INTO certificados (matricula_id, estado) VALUES (?, ?)",
                    (matricula_id, PENDIENTE),
                )
                codigo = f"CERT-{datetime.now():%Y}-{cur.lastrowid:06d}"
                c.execute("UPDATE certificados SET codigo = ? WHERE id = ?", (codigo, cur.lastrowid))
        except sqlite3.IntegrityError:
            raise FJPP_ErrorDeNegocio("Esta matrícula ya tiene un certificado solicitado.") from None
        return self.FJPP_obtener(codigo)

    # ------------------------------------------------------------------ paso 2
    def FJPP_generar_lote_envio(self, ids: list[int] | None = None) -> tuple[Path, int]:
        """Crea un CSV con los certificados pendientes y los marca como ENVIADO_A_FIRMA."""
        pendientes = self.FJPP_listar(PENDIENTE)
        if ids is not None:
            seleccion = set(ids)
            pendientes = [p for p in pendientes if p["id"] in seleccion]
        if not pendientes:
            raise FJPP_ErrorDeNegocio("No hay certificados pendientes de envío.")

        self.dir_solicitudes.mkdir(parents=True, exist_ok=True)
        ruta = self.dir_solicitudes / f"lote_{datetime.now():%Y%m%d_%H%M%S}.csv"
        with open(ruta, "w", newline="", encoding="utf-8-sig") as archivo:
            escritor = csv.writer(archivo)
            escritor.writerow(["codigo", "dni", "estudiante", "curso_codigo", "curso", "horas"])
            for p in pendientes:
                escritor.writerow(
                    [p["codigo"], p["dni"], p["estudiante"], p["curso_codigo"], p["curso"], p["horas"]]
                )
        try:
            with self.db.FJPP_transaccion() as c:
                c.executemany(
                    "UPDATE certificados SET estado = ?, fecha_envio = CURRENT_TIMESTAMP WHERE id = ?",
                    [(ENVIADO, p["id"]) for p in pendientes],
                )
        except BaseException:
            ruta.unlink(missing_ok=True)
            raise
        return ruta, len(pendientes)

    # ------------------------------------------------------------------ paso 3
    def FJPP_importar_pdf_firmado(self, codigo: str, ruta_pdf, permitir_sin_firma: bool = False) -> dict:
        certificado = self.FJPP_obtener(codigo)
        if certificado["estado"] == FIRMADO:
            raise FJPP_ErrorDeNegocio("Este certificado ya tiene su PDF firmado registrado.")

        origen = Path(str(ruta_pdf).strip().strip('"').strip("'")).expanduser()
        if not origen.is_file():
            raise FJPP_NoEncontrado(f"No se encontró el archivo: {origen}")
        datos = origen.read_bytes()
        if not firma_digital.FJPP_es_pdf(datos):
            raise FJPP_ErrorDeNegocio("El archivo no es un PDF válido.")

        huella = hashlib.sha256(datos).hexdigest()
        repetido = self.db.FJPP_consultar_uno("SELECT codigo FROM certificados WHERE sha256 = ?", (huella,))
        if repetido:
            raise FJPP_ErrorDeNegocio(f"Este mismo PDF ya fue registrado para {repetido['codigo']}.")

        firmas = firma_digital.FJPP_contar_firmas(datos)
        if firmas == 0 and not permitir_sin_firma:
            raise FJPP_ErrorDeNegocio(
                "No se detectó ninguna firma digital en el PDF. "
                "Verifique que sea la versión firmada que devolvió la oficina."
            )
        estado_verificacion, _detalle = firma_digital.FJPP_verificar(origen)
        if estado_verificacion == firma_digital.INVALIDA:
            raise FJPP_ErrorDeNegocio(
                "La firma digital del PDF no es íntegra (el documento pudo ser alterado)."
            )

        self.dir_certificados.mkdir(parents=True, exist_ok=True)
        nombre = f"{certificado['codigo']}.pdf"
        destino = self.dir_certificados / nombre
        shutil.copyfile(origen, destino)  # copia byte a byte: no se modifica la firma
        try:
            with self.db.FJPP_transaccion() as c:
                c.execute(
                    "UPDATE certificados SET estado = ?, fecha_firmado = CURRENT_TIMESTAMP, "
                    "archivo_pdf = ?, sha256 = ?, firmas_detectadas = ?, verificacion = ? "
                    "WHERE id = ?",
                    (FIRMADO, nombre, huella, firmas, estado_verificacion, certificado["id"]),
                )
        except BaseException:
            destino.unlink(missing_ok=True)
            raise
        return self.FJPP_obtener(certificado["codigo"])

    # ------------------------------------------------------------------ control
    def ruta_pdf(self, codigo: str) -> Path:
        cert = self.FJPP_obtener(codigo)
        if not cert["archivo_pdf"]:
            raise FJPP_ErrorDeNegocio("Este certificado todavía no tiene PDF firmado.")
        return self.dir_certificados / cert["archivo_pdf"]

    def FJPP_verificar_integridad(self, codigo: str) -> tuple[bool, str]:
        """Compara la huella guardada con la del archivo actual en disco."""
        cert = self.FJPP_obtener(codigo)
        if cert["estado"] != FIRMADO:
            raise FJPP_ErrorDeNegocio("Este certificado todavía no tiene PDF firmado.")
        ruta = self.dir_certificados / cert["archivo_pdf"]
        if not ruta.is_file():
            return False, f"Falta el archivo {ruta.name} en la carpeta de certificados."
        actual = hashlib.sha256(ruta.read_bytes()).hexdigest()
        if actual != cert["sha256"]:
            return False, "El archivo fue modificado después de registrarse (la huella no coincide)."
        return True, "El archivo coincide con la huella registrada."
