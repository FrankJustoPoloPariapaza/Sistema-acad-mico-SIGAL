"""Pruebas del flujo completo. Ejecutar:  python -m unittest discover -s tests -v"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from contexto import FJPP_Contexto
from core.database import FJPP_Database
from core.dinero import FJPP_a_centimos, FJPP_formatear
from core.excepciones import FJPP_ErrorDeNegocio, FJPP_ValidacionError

PDF_FIRMADO = (b"%PDF-1.7\n1 0 obj<< /Type /Sig /Filter /Adobe.PPKLite "
               b"/ByteRange [0 100 200 50] /Contents <00> >>endobj\n%%EOF\n")
PDF_SIN_FIRMA = b"%PDF-1.7\n1 0 obj<< /Type /Catalog >>endobj\n%%EOF\n"


class FJPP_PruebaFlujo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.db = FJPP_Database(":memory:")
        self.ctx = FJPP_Contexto(self.db, base / "certs", base / "lotes")
        self.base = base
        self.curso = self.ctx.cursos.FJPP_crear("exc-01", "Excel", 40, "180.50")
        self.est = self.ctx.estudiantes.FJPP_crear("12345678", "Ana", "Quispe")
        self.mat = self.ctx.matriculas.FJPP_matricular(self.est, self.curso)

    def tearDown(self):
        self.db.FJPP_cerrar()
        self.tmp.cleanup()

    def _FJPP_pdf(self, nombre, contenido):
        ruta = self.base / nombre
        ruta.write_bytes(contenido)
        return ruta

    def test_FJPP_dinero(self):
        self.assertEqual(FJPP_a_centimos("150,50"), 15050)
        self.assertEqual(FJPP_a_centimos("0.1") + FJPP_a_centimos("0.2"), 30)
        self.assertEqual(FJPP_formatear(1234567), "S/ 12,345.67")
        for malo in ("abc", "-5", "nan", "inf"):
            with self.assertRaises(FJPP_ValidacionError):
                FJPP_a_centimos(malo)

    def test_FJPP_validaciones_y_duplicados(self):
        with self.assertRaises(FJPP_ValidacionError):
            self.ctx.estudiantes.FJPP_crear("123", "A", "B")
        with self.assertRaises(FJPP_ErrorDeNegocio):
            self.ctx.estudiantes.FJPP_crear("12345678", "X", "Y")
        with self.assertRaises(FJPP_ErrorDeNegocio):
            self.ctx.matriculas.FJPP_matricular(self.est, self.curso)
        with self.assertRaises(FJPP_ValidacionError):
            self.ctx.estudiantes.FJPP_actualizar(self.est, dni="99999999")

    def test_FJPP_pagos_y_saldo(self):
        self.assertEqual(self.ctx.matriculas.FJPP_detalle(self.mat)["saldo_centimos"], 18050)
        p1 = self.ctx.pagos.FJPP_registrar(self.mat, "100", "efectivo")
        self.assertTrue(p1["nro_recibo"].startswith("REC-"))
        with self.assertRaises(FJPP_ErrorDeNegocio):   # excede saldo
            self.ctx.pagos.FJPP_registrar(self.mat, "80.51", "EFECTIVO")
        self.assertEqual(len(self.ctx.pagos.FJPP_deudores()), 1)
        self.ctx.pagos.FJPP_registrar(self.mat, "80.50", "EFECTIVO")
        self.assertEqual(self.ctx.pagos.FJPP_deudores(), [])
        self.ctx.pagos.FJPP_anular(p1["id"], "error de digitación")
        self.assertEqual(self.ctx.matriculas.FJPP_detalle(self.mat)["saldo_centimos"], 10000)

    def test_FJPP_certificado_requiere_completada_y_pagada(self):
        with self.assertRaises(FJPP_ErrorDeNegocio):
            self.ctx.certificados.FJPP_solicitar(self.mat)          # en curso
        self.ctx.matriculas.FJPP_cambiar_estado(self.mat, "COMPLETADA")
        with self.assertRaises(FJPP_ErrorDeNegocio):
            self.ctx.certificados.FJPP_solicitar(self.mat)          # con deuda
        self.ctx.pagos.FJPP_registrar(self.mat, "180.50", "EFECTIVO")
        cert = self.ctx.certificados.FJPP_solicitar(self.mat)
        self.assertEqual(cert["estado"], "PENDIENTE_FIRMA")
        with self.assertRaises(FJPP_ErrorDeNegocio):
            self.ctx.certificados.FJPP_solicitar(self.mat)          # duplicado

    def test_FJPP_flujo_completo_con_pdf_firmado(self):
        self.ctx.pagos.FJPP_registrar(self.mat, "180.50", "EFECTIVO")
        self.ctx.matriculas.FJPP_cambiar_estado(self.mat, "COMPLETADA")
        cert = self.ctx.certificados.FJPP_solicitar(self.mat)

        ruta_lote, n = self.ctx.certificados.FJPP_generar_lote_envio()
        self.assertEqual(n, 1)
        self.assertIn(cert["codigo"], ruta_lote.read_text(encoding="utf-8-sig"))
        self.assertEqual(self.ctx.certificados.FJPP_obtener(cert["codigo"])["estado"], "ENVIADO_A_FIRMA")

        with self.assertRaises(FJPP_ErrorDeNegocio):   # PDF sin firma
            self.ctx.certificados.FJPP_importar_pdf_firmado(
                cert["codigo"], self._FJPP_pdf("sin.pdf", PDF_SIN_FIRMA))
        with self.assertRaises(FJPP_ErrorDeNegocio):   # no es PDF
            self.ctx.certificados.FJPP_importar_pdf_firmado(
                cert["codigo"], self._FJPP_pdf("x.pdf", b"hola"))

        firmado = self._FJPP_pdf("firmado.pdf", PDF_FIRMADO)
        res = self.ctx.certificados.FJPP_importar_pdf_firmado(cert["codigo"], firmado)
        self.assertEqual(res["estado"], "FIRMADO")
        self.assertEqual(res["firmas_detectadas"], 1)
        guardado = self.ctx.certificados.ruta_pdf(cert["codigo"])
        self.assertEqual(guardado.read_bytes(), PDF_FIRMADO)     # copia exacta

        with self.assertRaises(FJPP_ErrorDeNegocio):   # ya firmado
            self.ctx.certificados.FJPP_importar_pdf_firmado(cert["codigo"], firmado)
        with self.assertRaises(FJPP_ErrorDeNegocio):   # no se anula pago con certificado
            self.ctx.pagos.FJPP_anular(self.ctx.pagos.FJPP_listar_por_matricula(self.mat)[0]["id"], "x")

        self.assertTrue(self.ctx.certificados.FJPP_verificar_integridad(cert["codigo"])[0])
        guardado.write_bytes(PDF_FIRMADO + b"alterado")
        self.assertFalse(self.ctx.certificados.FJPP_verificar_integridad(cert["codigo"])[0])

    def test_FJPP_mismo_pdf_en_dos_certificados(self):
        est2 = self.ctx.estudiantes.FJPP_crear("87654321", "Luis", "Perez")
        mat2 = self.ctx.matriculas.FJPP_matricular(est2, self.curso)
        codigos = []
        for m in (self.mat, mat2):
            self.ctx.pagos.FJPP_registrar(m, "180.50", "EFECTIVO")
            self.ctx.matriculas.FJPP_cambiar_estado(m, "COMPLETADA")
            codigos.append(self.ctx.certificados.FJPP_solicitar(m)["codigo"])
        pdf = self._FJPP_pdf("a.pdf", PDF_FIRMADO)
        self.ctx.certificados.FJPP_importar_pdf_firmado(codigos[0], pdf)
        with self.assertRaises(FJPP_ErrorDeNegocio):
            self.ctx.certificados.FJPP_importar_pdf_firmado(codigos[1], pdf)

    def test_FJPP_resumen_y_retiro(self):
        self.ctx.pagos.FJPP_registrar(self.mat, "50", "EFECTIVO")
        r = self.ctx.reportes.FJPP_resumen()
        self.assertEqual((r["facturado_centimos"], r["recaudado_centimos"]), (18050, 5000))
        self.ctx.matriculas.FJPP_cambiar_estado(self.mat, "RETIRADA")
        with self.assertRaises(FJPP_ErrorDeNegocio):
            self.ctx.pagos.FJPP_registrar(self.mat, "10", "EFECTIVO")
        self.assertEqual(self.ctx.reportes.FJPP_resumen()["facturado_centimos"], 0)


if __name__ == "__main__":
    unittest.FJPP_main()
