"""Menús de la aplicación de consola. Solo presentan datos y llaman a los módulos."""
from __future__ import annotations

import config
from contexto import FJPP_Contexto
from core.dinero import FJPP_formatear
from core.excepciones import FJPP_ErrorDeNegocio
from modulos import firma_digital
from modulos.certificados import ESTADOS
from modulos.matriculas import COMPLETADA, RETIRADA
from ui.consola import (FJPP_confirmar, FJPP_menu, FJPP_pedir, FJPP_pedir_entero, FJPP_tabla, titulo)


class FJPP_Aplicacion:
    def __init__(self, ctx: FJPP_Contexto):
        self.ctx = ctx

    # ---------------------------------------------------------------- helpers
    def _FJPP_elegir_matricula(self) -> dict:
        """Pide el DNI, lista las matrículas del estudiante y pide cuál usar."""
        estudiante = self.ctx.estudiantes.FJPP_obtener_por_dni(FJPP_pedir("DNI del estudiante"))
        matriculas = self.ctx.matriculas.FJPP_listar_por_estudiante(estudiante["id"])
        if not matriculas:
            raise FJPP_ErrorDeNegocio("El estudiante no tiene matrículas.")
        print(f"\n  {estudiante['apellidos']}, {estudiante['nombres']}")
        self._FJPP_mostrar_matriculas(matriculas)
        if len(matriculas) == 1:
            return matriculas[0]
        elegido = FJPP_pedir_entero("ID de la matrícula")
        for m in matriculas:
            if m["id"] == elegido:
                return m
        raise FJPP_ErrorDeNegocio("Esa matrícula no pertenece al estudiante.")

    @staticmethod
    def _FJPP_mostrar_matriculas(matriculas: list[dict]) -> None:
        filas = [
            {**m, "monto": FJPP_formatear(m["monto_centimos"]),
             "pagado": FJPP_formatear(m["pagado_centimos"]),
             "saldo": FJPP_formatear(m["saldo_centimos"])}
            for m in matriculas
        ]
        FJPP_tabla(filas, [("ID", "id"), ("Curso", "curso_codigo"), ("Nombre", "curso"),
                      ("Estado", "estado"), ("Monto", "monto"), ("Pagado", "pagado"),
                      ("Saldo", "saldo")])

    # ------------------------------------------------------------ estudiantes
    def FJPP_est_registrar(self):
        nuevo_id = self.ctx.estudiantes.FJPP_crear(
            FJPP_pedir("DNI (8 dígitos)"), FJPP_pedir("Nombres"), FJPP_pedir("Apellidos"),
            FJPP_pedir("Correo (opcional)", obligatorio=False),
            FJPP_pedir("Teléfono (opcional)", obligatorio=False),
        )
        print(f"\n  Estudiante registrado (id {nuevo_id}).")

    def FJPP_est_buscar(self):
        texto = FJPP_pedir("Buscar por DNI, nombre o apellido (vacío = todos)", obligatorio=False)
        FJPP_tabla(self.ctx.estudiantes.FJPP_buscar(texto),
              [("ID", "id"), ("DNI", "dni"), ("Apellidos", "apellidos"),
               ("Nombres", "nombres"), ("Correo", "email"), ("Teléfono", "telefono")])

    def FJPP_est_estado_cuenta(self):
        est = self.ctx.estudiantes.FJPP_obtener_por_dni(FJPP_pedir("DNI del estudiante"))
        print(f"\n  {est['apellidos']}, {est['nombres']}  (DNI {est['dni']})")
        cuenta = self.ctx.pagos.FJPP_estado_de_cuenta(est["id"])
        self._FJPP_mostrar_matriculas(cuenta)
        if cuenta:
            print(f"\n  Saldo total: {FJPP_formatear(sum(m['saldo_centimos'] for m in cuenta if m['estado'] != RETIRADA))}")
        certs = self.ctx.certificados.FJPP_listar_por_estudiante(est["id"])
        if certs:
            print("\n  Certificados:")
            FJPP_tabla(certs, [("Código", "codigo"), ("Curso", "curso_codigo"), ("Estado", "estado")])

    def FJPP_est_editar(self):
        est = self.ctx.estudiantes.FJPP_obtener_por_dni(FJPP_pedir("DNI del estudiante"))
        self.ctx.estudiantes.FJPP_actualizar(
            est["id"],
            nombres=FJPP_pedir("Nombres", est["nombres"]),
            apellidos=FJPP_pedir("Apellidos", est["apellidos"]),
            email=FJPP_pedir("Correo", est["email"], obligatorio=False),
            telefono=FJPP_pedir("Teléfono", est["telefono"], obligatorio=False),
        )
        print("\n  Datos actualizados.")

    def FJPP_est_desactivar(self):
        est = self.ctx.estudiantes.FJPP_obtener_por_dni(FJPP_pedir("DNI del estudiante"))
        if FJPP_confirmar(f"¿Desactivar a {est['nombres']} {est['apellidos']}?"):
            self.ctx.estudiantes.FJPP_desactivar(est["id"])
            print("\n  Estudiante desactivado.")

    # ----------------------------------------------------------------- cursos
    def FJPP_cur_crear(self):
        nuevo_id = self.ctx.cursos.FJPP_crear(
            FJPP_pedir("Código (ej. EXC-01)"), FJPP_pedir("Nombre"),
            FJPP_pedir("Horas"), FJPP_pedir(f"Precio ({config.MONEDA})"),
        )
        print(f"\n  Curso creado (id {nuevo_id}).")

    def FJPP_cur_listar(self):
        cursos = [{**c, "precio": FJPP_formatear(c["precio_centimos"])}
                  for c in self.ctx.cursos.FJPP_listar()]
        FJPP_tabla(cursos, [("ID", "id"), ("Código", "codigo"), ("Nombre", "nombre"),
                       ("Horas", "horas"), ("Precio", "precio")])

    def FJPP_cur_cambiar_precio(self):
        curso = self.ctx.cursos.FJPP_obtener_por_codigo(FJPP_pedir("Código del curso"))
        print(f"  Precio actual: {FJPP_formatear(curso['precio_centimos'])}")
        self.ctx.cursos.FJPP_cambiar_precio(curso["id"], FJPP_pedir("Nuevo precio"))
        print("\n  Precio actualizado (las matrículas existentes conservan su monto).")

    def FJPP_cur_desactivar(self):
        curso = self.ctx.cursos.FJPP_obtener_por_codigo(FJPP_pedir("Código del curso"))
        if FJPP_confirmar(f"¿Desactivar el curso {curso['nombre']}?"):
            self.ctx.cursos.FJPP_desactivar(curso["id"])
            print("\n  Curso desactivado.")

    def FJPP_cur_alumnos(self):
        curso = self.ctx.cursos.FJPP_obtener_por_codigo(FJPP_pedir("Código del curso"))
        filas = [{**m, "saldo": FJPP_formatear(m["saldo_centimos"])}
                 for m in self.ctx.matriculas.FJPP_listar_por_curso(curso["id"])]
        print(f"\n  {curso['codigo']} - {curso['nombre']}")
        FJPP_tabla(filas, [("Matr.", "id"), ("DNI", "dni"), ("Estudiante", "estudiante"),
                      ("Estado", "estado"), ("Saldo", "saldo")])

    # ------------------------------------------------------------- matrículas
    def FJPP_mat_matricular(self):
        est = self.ctx.estudiantes.FJPP_obtener_por_dni(FJPP_pedir("DNI del estudiante"))
        curso = self.ctx.cursos.FJPP_obtener_por_codigo(FJPP_pedir("Código del curso"))
        monto = FJPP_pedir(f"Monto a pagar ({config.MONEDA})",
                      f"{curso['precio_centimos'] / 100:.2f}")
        matricula_id = self.ctx.matriculas.FJPP_matricular(est["id"], curso["id"], monto)
        print(f"\n  Matrícula registrada (id {matricula_id}).")

    def FJPP_mat_ver(self):
        est = self.ctx.estudiantes.FJPP_obtener_por_dni(FJPP_pedir("DNI del estudiante"))
        self._FJPP_mostrar_matriculas(self.ctx.matriculas.FJPP_listar_por_estudiante(est["id"]))

    def FJPP_mat_completar(self):
        m = self._FJPP_elegir_matricula()
        if FJPP_confirmar(f"¿Marcar {m['curso_codigo']} como COMPLETADA?"):
            self.ctx.matriculas.FJPP_cambiar_estado(m["id"], COMPLETADA)
            print("\n  Matrícula completada.")

    def FJPP_mat_retirar(self):
        m = self._FJPP_elegir_matricula()
        if FJPP_confirmar(f"¿Retirar al estudiante de {m['curso_codigo']}?"):
            self.ctx.matriculas.FJPP_cambiar_estado(m["id"], RETIRADA)
            print("\n  Matrícula retirada.")

    # ------------------------------------------------------------------ pagos
    def FJPP_pag_registrar(self):
        m = self._FJPP_elegir_matricula()
        print(f"\n  Saldo pendiente: {FJPP_formatear(m['saldo_centimos'])}")
        pago = self.ctx.pagos.FJPP_registrar(
            m["id"],
            FJPP_pedir(f"Monto ({config.MONEDA})"),
            FJPP_pedir(f"Método ({'/'.join(config.METODOS_PAGO)})", "EFECTIVO"),
            FJPP_pedir("Referencia / N° de operación (opcional)", obligatorio=False),
        )
        print(f"\n  Pago registrado. Recibo: {pago['nro_recibo']}")

    def FJPP_pag_historial(self):
        m = self._FJPP_elegir_matricula()
        pagos = [{**p, "monto": FJPP_formatear(p["monto_centimos"]),
                  "estado": "ANULADO" if p["anulado"] else "OK"}
                 for p in self.ctx.pagos.FJPP_listar_por_matricula(m["id"])]
        FJPP_tabla(pagos, [("ID", "id"), ("Recibo", "nro_recibo"), ("Fecha", "fecha"),
                      ("Monto", "monto"), ("Método", "metodo"), ("Ref.", "referencia"),
                      ("Estado", "estado")])

    def FJPP_pag_anular(self):
        m = self._FJPP_elegir_matricula()
        pagos = [{**p, "monto": FJPP_formatear(p["monto_centimos"])}
                 for p in self.ctx.pagos.FJPP_listar_por_matricula(m["id"], incluir_anulados=False)]
        FJPP_tabla(pagos, [("ID", "id"), ("Recibo", "nro_recibo"), ("Fecha", "fecha"),
                      ("Monto", "monto")])
        if not pagos:
            return
        pago_id = FJPP_pedir_entero("ID del pago a anular")
        motivo = FJPP_pedir("Motivo de la anulación")
        if FJPP_confirmar("¿Confirmar la anulación?"):
            self.ctx.pagos.FJPP_anular(pago_id, motivo)
            print("\n  Pago anulado.")

    def FJPP_pag_deudores(self):
        filas = [{**d, "saldo": FJPP_formatear(d["saldo_centimos"])} for d in self.ctx.pagos.FJPP_deudores()]
        FJPP_tabla(filas, [("DNI", "dni"), ("Estudiante", "estudiante"), ("Curso", "curso_codigo"),
                      ("Estado", "estado"), ("Saldo", "saldo")])
        if filas:
            total = sum(d["saldo_centimos"] for d in self.ctx.pagos.FJPP_deudores())
            print(f"\n  Total por cobrar: {FJPP_formatear(total)}")

    # ----------------------------------------------------------- certificados
    def FJPP_cer_solicitar(self):
        m = self._FJPP_elegir_matricula()
        cert = self.ctx.certificados.FJPP_solicitar(m["id"])
        print(f"\n  Certificado solicitado: {cert['codigo']} (pendiente de firma).")

    def FJPP_cer_lote(self):
        pendientes = self.ctx.certificados.FJPP_listar("PENDIENTE_FIRMA")
        FJPP_tabla(pendientes, [("Código", "codigo"), ("DNI", "dni"),
                           ("Estudiante", "estudiante"), ("Curso", "curso_codigo")])
        if pendientes and FJPP_confirmar(f"¿Generar el lote con {len(pendientes)} certificado(s)?"):
            ruta, cantidad = self.ctx.certificados.FJPP_generar_lote_envio()
            print(f"\n  Lote generado con {cantidad} certificado(s):\n  {ruta}")

    def FJPP_cer_importar(self):
        codigo = FJPP_pedir("Código del certificado (ej. CERT-2026-000001)")
        ruta = FJPP_pedir("Ruta del PDF firmado (puede arrastrar el archivo aquí)")
        try:
            cert = self.ctx.certificados.FJPP_importar_pdf_firmado(codigo, ruta)
        except FJPP_ErrorDeNegocio as error:
            if "No se detectó ninguna firma" not in str(error):
                raise
            print(f"\n  [!] {error}")
            if not FJPP_confirmar("¿Registrarlo de todos modos, sin firma detectada?"):
                return
            cert = self.ctx.certificados.FJPP_importar_pdf_firmado(codigo, ruta, permitir_sin_firma=True)
        print(f"\n  Certificado {cert['codigo']} registrado como FIRMADO.")
        print(f"  Firmas detectadas: {cert['firmas_detectadas']} | Verificación: {cert['verificacion']}")
        if cert["verificacion"] == firma_digital.NO_VERIFICADA:
            print("  (Instale pyHanko para comprobar la integridad criptográfica de la firma.)")

    def FJPP_cer_listar(self):
        estado = FJPP_pedir(f"Estado ({'/'.join(ESTADOS)}; vacío = todos)", obligatorio=False).upper()
        FJPP_tabla(self.ctx.certificados.FJPP_listar(estado or None),
              [("Código", "codigo"), ("DNI", "dni"), ("Estudiante", "estudiante"),
               ("Curso", "curso_codigo"), ("Estado", "estado"), ("Verif.", "verificacion")])

    def FJPP_cer_integridad(self):
        ok, mensaje = self.ctx.certificados.FJPP_verificar_integridad(FJPP_pedir("Código del certificado"))
        print(f"\n  {'OK' if ok else 'ALERTA'}: {mensaje}")

    # --------------------------------------------------------------- reportes
    def FJPP_rep_resumen(self):
        r = self.ctx.reportes.FJPP_resumen()
        print(f"\n  Estudiantes activos : {r['estudiantes_activos']}")
        print(f"  Cursos activos      : {r['cursos_activos']}")
        print(f"  Matrículas en curso : {r['matriculas_en_curso']}")
        print(f"  Facturado           : {FJPP_formatear(r['facturado_centimos'])}")
        print(f"  Recaudado           : {FJPP_formatear(r['recaudado_centimos'])}")
        print(f"  Por cobrar          : {FJPP_formatear(r['por_cobrar_centimos'])}")
        print("  Certificados        : " +
              ", ".join(f"{k}={v}" for k, v in r["certificados"].items()))

    # ------------------------------------------------------------------- menú
    def FJPP_ejecutar(self) -> None:
        titulo("SISTEMA ACADÉMICO — Pagos, cursos y certificados")
        FJPP_menu("MENÚ PRINCIPAL", [
            ("Estudiantes", lambda: FJPP_menu("ESTUDIANTES", [
                ("Registrar estudiante", self.FJPP_est_registrar),
                ("Buscar / listar", self.FJPP_est_buscar),
                ("Estado de cuenta y certificados", self.FJPP_est_estado_cuenta),
                ("Editar datos de contacto", self.FJPP_est_editar),
                ("Desactivar estudiante", self.FJPP_est_desactivar)])),
            ("Cursos", lambda: FJPP_menu("CURSOS", [
                ("Crear curso", self.FJPP_cur_crear),
                ("Listar cursos", self.FJPP_cur_listar),
                ("Ver alumnos de un curso", self.FJPP_cur_alumnos),
                ("Cambiar precio", self.FJPP_cur_cambiar_precio),
                ("Desactivar curso", self.FJPP_cur_desactivar)])),
            ("Matrículas", lambda: FJPP_menu("MATRÍCULAS", [
                ("Matricular estudiante en un curso", self.FJPP_mat_matricular),
                ("Ver matrículas de un estudiante", self.FJPP_mat_ver),
                ("Marcar matrícula como completada", self.FJPP_mat_completar),
                ("Retirar estudiante de un curso", self.FJPP_mat_retirar)])),
            ("Pagos", lambda: FJPP_menu("PAGOS", [
                ("Registrar pago", self.FJPP_pag_registrar),
                ("Historial de pagos de una matrícula", self.FJPP_pag_historial),
                ("Anular pago", self.FJPP_pag_anular),
                ("Estudiantes con deuda", self.FJPP_pag_deudores)])),
            ("Certificados", lambda: FJPP_menu("CERTIFICADOS", [
                ("Solicitar certificado (matrícula completada y pagada)", self.FJPP_cer_solicitar),
                ("Generar lote para enviar a firma", self.FJPP_cer_lote),
                ("Registrar PDF firmado recibido", self.FJPP_cer_importar),
                ("Listar certificados", self.FJPP_cer_listar),
                ("Verificar integridad de un PDF guardado", self.FJPP_cer_integridad)])),
            ("Reportes", lambda: FJPP_menu("REPORTES", [("Resumen general", self.FJPP_rep_resumen)])),
        ], salida="Salir")
        print("\n  Hasta luego.")
