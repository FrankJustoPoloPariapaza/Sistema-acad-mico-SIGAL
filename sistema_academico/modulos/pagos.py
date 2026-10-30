"""Módulo de pagos de estudiantes."""
from __future__ import annotations

from datetime import datetime

from core.database import FJPP_Database
from core.dinero import FJPP_a_centimos, FJPP_formatear
from core.excepciones import FJPP_ErrorDeNegocio, FJPP_NoEncontrado, FJPP_ValidacionError
from core.validadores import FJPP_hoy_iso, FJPP_requerido, FJPP_validar_fecha
from modulos.matriculas import RETIRADA, FJPP_ServicioMatriculas


class FJPP_ServicioPagos:
    def __init__(self, db: FJPP_Database, matriculas: FJPP_ServicioMatriculas):
        self.db = db
        self.matriculas = matriculas

    def FJPP_registrar(self, matricula_id: int, monto, metodo: str, referencia: str = "",
                  fecha=None) -> dict:
        matricula = self.matriculas.FJPP_detalle(matricula_id)
        if matricula["estado"] == RETIRADA:
            raise FJPP_ErrorDeNegocio("No se pueden registrar pagos en una matrícula RETIRADA.")
        centimos = FJPP_a_centimos(monto)
        if centimos <= 0:
            raise FJPP_ValidacionError("El monto debe ser mayor que cero.")
        if centimos > matricula["saldo_centimos"]:
            raise FJPP_ErrorDeNegocio(
                f"El pago ({FJPP_formatear(centimos)}) excede el saldo pendiente "
                f"({FJPP_formatear(matricula['saldo_centimos'])})."
            )
        metodo = FJPP_requerido(metodo, "El método de pago").upper()
        fecha_iso = FJPP_hoy_iso() if not fecha else FJPP_validar_fecha(fecha)

        with self.db.FJPP_transaccion() as c:
            cur = c.execute(
                "INSERT INTO pagos (matricula_id, monto_centimos, fecha, metodo, referencia) "
                "VALUES (?, ?, ?, ?, ?)",
                (matricula_id, centimos, fecha_iso, metodo, (referencia or "").strip()),
            )
            recibo = f"REC-{datetime.now():%Y}-{cur.lastrowid:06d}"
            c.execute("UPDATE pagos SET nro_recibo = ? WHERE id = ?", (recibo, cur.lastrowid))
            pago_id = cur.lastrowid
        return self.FJPP_obtener(pago_id)

    def FJPP_obtener(self, pago_id: int) -> dict:
        fila = self.db.FJPP_consultar_uno("SELECT * FROM pagos WHERE id = ?", (pago_id,))
        if fila is None:
            raise FJPP_NoEncontrado(f"No existe el pago con id {pago_id}.")
        return dict(fila)

    def FJPP_listar_por_matricula(self, matricula_id: int, incluir_anulados: bool = True) -> list[dict]:
        sql = "SELECT * FROM pagos WHERE matricula_id = ? "
        if not incluir_anulados:
            sql += "AND anulado = 0 "
        sql += "ORDER BY fecha, id"
        return [dict(f) for f in self.db.FJPP_consultar(sql, (matricula_id,))]

    def FJPP_anular(self, pago_id: int, motivo: str) -> None:
        pago = self.FJPP_obtener(pago_id)
        if pago["anulado"]:
            raise FJPP_ErrorDeNegocio("Este pago ya está anulado.")
        motivo = FJPP_requerido(motivo, "El motivo de anulación")
        cert = self.db.FJPP_consultar_uno(
            "SELECT codigo FROM certificados WHERE matricula_id = ?", (pago["matricula_id"],)
        )
        if cert:
            raise FJPP_ErrorDeNegocio(
                f"No se puede anular: la matrícula ya tiene el certificado {cert['codigo']}."
            )
        with self.db.FJPP_transaccion() as c:
            c.execute(
                "UPDATE pagos SET anulado = 1, motivo_anulacion = ? WHERE id = ?",
                (motivo, pago_id),
            )

    def FJPP_estado_de_cuenta(self, estudiante_id: int) -> list[dict]:
        """Una fila por matrícula con monto, pagado y saldo."""
        return self.matriculas.FJPP_listar_por_estudiante(estudiante_id)

    def FJPP_deudores(self) -> list[dict]:
        """Matrículas con saldo pendiente (excluye las retiradas)."""
        filas = self.db.FJPP_consultar(
            """
            SELECT e.dni, e.nombres || ' ' || e.apellidos AS estudiante,
                   c.codigo AS curso_codigo, m.id AS matricula_id, m.estado,
                   m.monto_centimos,
                   COALESCE(SUM(CASE WHEN p.anulado = 0 THEN p.monto_centimos END), 0)
                       AS pagado_centimos
            FROM matriculas m
            JOIN estudiantes e ON e.id = m.estudiante_id
            JOIN cursos c ON c.id = m.curso_id
            LEFT JOIN pagos p ON p.matricula_id = m.id
            WHERE m.estado != 'RETIRADA'
            GROUP BY m.id
            HAVING m.monto_centimos - pagado_centimos > 0
            ORDER BY e.apellidos, e.nombres
            """
        )
        resultado = []
        for fila in filas:
            datos = dict(fila)
            datos["saldo_centimos"] = datos["monto_centimos"] - datos["pagado_centimos"]
            resultado.append(datos)
        return resultado
