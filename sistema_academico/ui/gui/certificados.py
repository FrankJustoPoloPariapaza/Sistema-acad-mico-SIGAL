"""Página de certificados: solicitud → lote de envío → PDF firmado recibido."""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from core.excepciones import FJPP_ErrorDeNegocio
from modulos import firma_digital
from modulos.certificados import ENVIADO, ESTADOS, FIRMADO, PENDIENTE
from ui.gui import tema
from ui.gui.base import (FJPP_Pestana, FJPP_Tabla, FJPP_Tarjeta, FJPP_abrir_archivo, FJPP_barra_botones, FJPP_ejecutar_seguro,
                         FJPP_mostrar_error)

TODOS = "Todos"
TEXTO_ESTADO = {PENDIENTE: "Pendiente de firma", ENVIADO: "Enviado a firma", FIRMADO: "Firmado"}
COLOR_ESTADO = {PENDIENTE: tema.AVISO, ENVIADO: tema.ACENTO, FIRMADO: tema.OK}


class FJPP_PestanaCertificados(FJPP_Pestana):
    def __init__(self, parent, ctx):
        super().__init__(parent, ctx)
        self.filtro = tk.StringVar(value=TODOS)

        arriba = ttk.Frame(self)
        arriba.pack(fill="x", pady=(0, 10))
        combo = ttk.Combobox(arriba, textvariable=self.filtro, state="readonly", width=24,
                             values=[TODOS, *[TEXTO_ESTADO[e] for e in ESTADOS]])
        combo.pack(side="left")
        combo.bind("<<ComboboxSelected>>", lambda _e: self.FJPP_refrescar())
        ttk.Label(arriba, text="Filtrar por estado", style="Muted.TLabel").pack(side="left", padx=10)
        ttk.Label(arriba, text="Los certificados se solicitan desde Matrículas y pagos.",
                  style="Muted.TLabel").pack(side="right")

        tarjeta = FJPP_Tarjeta(self, relleno=0)
        tarjeta.pack(fill="both", expand=True)
        self.FJPP_tabla = FJPP_Tabla(tarjeta.cuerpo, [
            ("codigo", "Código", 140), ("dni", "DNI", 85), ("estudiante", "Estudiante", 200),
            ("curso_codigo", "Curso", 75), ("estado_txt", "Estado", 140),
            ("fecha_firmado", "Firmado el", 135), ("firmas_detectadas", "Firmas", 60, "center"),
            ("verificacion", "Verificación", 115),
        ], alto=16, clave_id="codigo")
        self.FJPP_tabla.pack(fill="both", expand=True)
        self.FJPP_tabla.tree.tag_configure("pendiente", foreground=tema.AVISO)
        self.FJPP_tabla.tree.tag_configure("enviado", foreground=tema.ACENTO)
        self.FJPP_tabla.tree.tag_configure("firmado", foreground=tema.OK)
        self.FJPP_tabla.tree.bind("<Double-1>", lambda _e: self.FJPP_ver_pdf())

        FJPP_barra_botones(self, [("Generar lote de envío", self.FJPP_generar_lote, "primary"),
                             ("Importar PDF firmado", self.FJPP_importar),
                             ("Ver PDF", self.FJPP_ver_pdf),
                             ("Verificar integridad", self.FJPP_verificar)]).pack(anchor="w", pady=(12, 0))

    def FJPP_refrescar(self) -> None:
        seleccion = self.filtro.get()
        estado = next((e for e in ESTADOS if TEXTO_ESTADO[e] == seleccion), None)
        ok, filas = FJPP_ejecutar_seguro(self, self.ctx.certificados.FJPP_listar, estado)
        if ok:
            for f in filas:
                f["estado_txt"] = TEXTO_ESTADO.get(f["estado"], f["estado"])
            self.FJPP_tabla.FJPP_cargar(filas, etiqueta=lambda f: {PENDIENTE: "pendiente", ENVIADO: "enviado",
                                                         FIRMADO: "firmado"}.get(f["estado"], ""))

    def FJPP_generar_lote(self) -> None:
        ok, pendientes = FJPP_ejecutar_seguro(self, self.ctx.certificados.FJPP_listar, PENDIENTE)
        if not ok:
            return
        if not pendientes:
            messagebox.showinfo("Sin pendientes", "No hay certificados pendientes de envío.", parent=self)
            return
        if not messagebox.askyesno("Generar lote",
                                   f"Se enviarán {len(pendientes)} certificado(s) a la oficina que "
                                   "firma.\nSe creará un archivo CSV y pasarán a 'Enviado a firma'.\n\n"
                                   "¿Continuar?", parent=self):
            return
        ok, resultado = FJPP_ejecutar_seguro(self, self.ctx.certificados.FJPP_generar_lote_envio)
        if ok:
            ruta, cantidad = resultado
            messagebox.showinfo("Lote generado", f"{cantidad} certificado(s) en:\n{ruta}", parent=self)
            self.FJPP_refrescar()

    def FJPP_importar(self) -> None:
        cert = self.FJPP_tabla.FJPP_requerir(self, "Seleccione el certificado cuyo PDF firmado recibió.")
        if not cert:
            return
        if cert["estado"] == FIRMADO:
            messagebox.showinfo("Ya registrado", "Este certificado ya tiene su PDF firmado.", parent=self)
            return
        ruta = filedialog.askopenfilename(
            parent=self, title=f"PDF firmado de {cert['codigo']}",
            filetypes=[("Documentos PDF", "*.pdf"), ("Todos los archivos", "*.*")])
        if not ruta:
            return
        servicio = self.ctx.certificados
        try:
            resultado = servicio.FJPP_importar_pdf_firmado(cert["codigo"], ruta)
        except Exception as error:
            if not (isinstance(error, FJPP_ErrorDeNegocio) and "No se detectó ninguna firma" in str(error)):
                FJPP_mostrar_error(self, error)
                return
            if not messagebox.askyesno("PDF sin firma detectada",
                                       f"{error}\n\n¿Registrarlo de todos modos?", parent=self,
                                       icon="warning"):
                return
            ok, resultado = FJPP_ejecutar_seguro(self, servicio.FJPP_importar_pdf_firmado, cert["codigo"],
                                            ruta, permitir_sin_firma=True)
            if not ok:
                return
        aviso = ""
        if resultado["verificacion"] == firma_digital.NO_VERIFICADA:
            aviso = ("\n\nNo se comprobó criptográficamente la firma. Instale pyHanko "
                     "(pip install pyhanko) para verificar que no fue alterada.")
        messagebox.showinfo("PDF registrado",
                            f"{resultado['codigo']} quedó como FIRMADO.\n"
                            f"Firmas detectadas: {resultado['firmas_detectadas']}\n"
                            f"Verificación: {resultado['verificacion']}{aviso}", parent=self)
        self.FJPP_refrescar()

    def FJPP_ver_pdf(self) -> None:
        cert = self.FJPP_tabla.FJPP_requerir(self, "Seleccione un certificado.")
        if not cert:
            return
        ok, ruta = FJPP_ejecutar_seguro(self, self.ctx.certificados.ruta_pdf, cert["codigo"])
        if ok:
            FJPP_ejecutar_seguro(self, FJPP_abrir_archivo, ruta)

    def FJPP_verificar(self) -> None:
        cert = self.FJPP_tabla.FJPP_requerir(self, "Seleccione un certificado.")
        if not cert:
            return
        ok, resultado = FJPP_ejecutar_seguro(self, self.ctx.certificados.FJPP_verificar_integridad, cert["codigo"])
        if ok:
            correcto, mensaje = resultado
            (messagebox.showinfo if correcto else messagebox.showwarning)(
                "Integridad del archivo" if correcto else "¡Alerta de integridad!", mensaje, parent=self)
