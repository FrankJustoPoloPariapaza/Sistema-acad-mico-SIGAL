"""Página de matrículas y pagos: se elige un estudiante y se ven sus cursos y abonos."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

import config
from core.dinero import FJPP_formatear
from modulos.matriculas import COMPLETADA, RETIRADA
from ui.gui import tema
from ui.gui.base import (FJPP_Formulario, FJPP_Pestana, FJPP_Tabla, FJPP_Tarjeta, FJPP_barra_botones, FJPP_ejecutar_seguro)


class FJPP_PestanaMatriculas(FJPP_Pestana):
    def __init__(self, parent, ctx):
        super().__init__(parent, ctx)
        self.texto = tk.StringVar()
        self.estudiante: dict | None = None

        panel = ttk.PanedWindow(self, orient="horizontal")
        panel.pack(fill="both", expand=True)

        # ---- izquierda: estudiantes
        izq = ttk.Frame(panel)
        ttk.Entry(izq, textvariable=self.texto).pack(fill="x")
        ttk.Label(izq, text="Buscar estudiante por DNI o nombre", style="Muted.TLabel").pack(
            anchor="w", pady=(4, 8))
        self.texto.trace_add("write", lambda *_: self._FJPP_cargar_estudiantes())
        t = FJPP_Tarjeta(izq, relleno=0)
        t.pack(fill="both", expand=True)
        self.estudiantes = FJPP_Tabla(t.cuerpo, [("dni", "DNI", 80), ("nombre", "Nombre", 170)],
                                 alto=18, al_seleccionar=self._FJPP_elegir_estudiante)
        self.estudiantes.pack(fill="both", expand=True)
        panel.add(izq, weight=1)

        # ---- derecha: matrículas y pagos
        der = ttk.Frame(panel, padding=(12, 0, 0, 0))
        self.titulo = ttk.Label(der, text="Seleccione un estudiante", font=tema.F["card"])
        self.titulo.pack(anchor="w", pady=(0, 8))

        tm = FJPP_Tarjeta(der, "Cursos matriculados")
        tm.pack(fill="both", expand=True)
        self.matriculas = FJPP_Tabla(tm.cuerpo, [
            ("curso_codigo", "Código", 70), ("curso", "Curso", 190), ("estado", "Estado", 90),
            ("monto", "Monto", 80, "e"), ("pagado", "Pagado", 80, "e"), ("saldo", "Saldo", 80, "e"),
            ("certificado", "Certificado", 120),
        ], alto=5, al_seleccionar=lambda _f: self._FJPP_cargar_pagos())
        self.matriculas.pack(fill="both", expand=True)
        self.matriculas.tree.tag_configure("deuda", foreground=tema.PELIGRO)
        self.matriculas.tree.tag_configure("retirada", foreground="#94a3b8")
        self.matriculas.tree.tag_configure("pagada", foreground=tema.OK)
        FJPP_barra_botones(tm.cuerpo, [("+ Matricular", self.FJPP_matricular, "primary"),
                                  ("Marcar completada", lambda: self._FJPP_cambiar(COMPLETADA)),
                                  ("Retirar", lambda: self._FJPP_cambiar(RETIRADA), "danger"),
                                  ("Solicitar certificado", self.FJPP_solicitar_certificado)],
                      tarjeta=True).pack(anchor="w", pady=(10, 0))

        tp = FJPP_Tarjeta(der, "Pagos de la matrícula seleccionada")
        tp.pack(fill="both", expand=True, pady=(10, 0))
        self.saldo = ttk.Label(tp.cuerpo, text="", style="CardMuted.TLabel")
        self.saldo.pack(anchor="w", pady=(0, 6))
        self.pagos = FJPP_Tabla(tp.cuerpo, [
            ("nro_recibo", "Recibo", 120), ("fecha", "Fecha", 90), ("monto", "Monto", 90, "e"),
            ("metodo", "Método", 110), ("referencia", "Referencia", 130), ("estado", "Estado", 80),
        ], alto=4)
        self.pagos.pack(fill="both", expand=True)
        self.pagos.tree.tag_configure("anulado", foreground="#94a3b8")
        FJPP_barra_botones(tp.cuerpo, [("+ Registrar pago", self.FJPP_registrar_pago, "primary"),
                                  ("Anular pago", self.FJPP_anular_pago, "danger")],
                      tarjeta=True).pack(anchor="w", pady=(10, 0))
        panel.add(der, weight=3)

    # ----------------------------------------------------------------- carga
    def FJPP_refrescar(self) -> None:
        self._FJPP_cargar_estudiantes()

    def _FJPP_cargar_estudiantes(self) -> None:
        ok, filas = FJPP_ejecutar_seguro(self, self.ctx.estudiantes.FJPP_buscar, self.texto.get().strip())
        if ok:
            for f in filas:
                f["nombre"] = f"{f['apellidos']}, {f['nombres']}"
            self.estudiantes.FJPP_cargar(filas)
            self._FJPP_elegir_estudiante(self.estudiantes.FJPP_seleccionada())

    def _FJPP_elegir_estudiante(self, fila: dict | None) -> None:
        self.estudiante = fila
        self._FJPP_cargar_matriculas()

    def _FJPP_cargar_matriculas(self) -> None:
        if not self.estudiante:
            self.titulo.config(text="Seleccione un estudiante")
            self.matriculas.FJPP_cargar([])
            self._FJPP_cargar_pagos()
            return
        e = self.estudiante
        self.titulo.config(text=f"{e['apellidos']}, {e['nombres']}   ·   DNI {e['dni']}")
        ok, filas = FJPP_ejecutar_seguro(self, self.ctx.matriculas.FJPP_listar_por_estudiante, e["id"])
        if not ok:
            return
        certificados = {c["matricula_id"]: c["estado"]
                        for c in self.ctx.certificados.FJPP_listar_por_estudiante(e["id"])}
        for m in filas:
            m["monto"] = FJPP_formatear(m["monto_centimos"])
            m["pagado"] = FJPP_formatear(m["pagado_centimos"])
            m["saldo"] = FJPP_formatear(m["saldo_centimos"])
            m["certificado"] = certificados.get(m["id"], "—")

        def etiqueta(m):
            if m["estado"] == RETIRADA:
                return "retirada"
            return "deuda" if m["saldo_centimos"] > 0 else "pagada"

        self.matriculas.FJPP_cargar(filas, etiqueta=etiqueta)
        self._FJPP_cargar_pagos()

    def _FJPP_cargar_pagos(self) -> None:
        m = self.matriculas.FJPP_seleccionada()
        if not m:
            self.pagos.FJPP_cargar([])
            self.saldo.config(text="Seleccione una matrícula para ver sus pagos.")
            return
        ok, filas = FJPP_ejecutar_seguro(self, self.ctx.pagos.FJPP_listar_por_matricula, m["id"])
        if ok:
            for p in filas:
                p["monto"] = FJPP_formatear(p["monto_centimos"])
                p["estado"] = "ANULADO" if p["anulado"] else "OK"
            self.pagos.FJPP_cargar(filas, etiqueta=lambda p: "anulado" if p["anulado"] else "")
            self.saldo.config(text=f"{m['curso_codigo']}  ·  monto {m['monto']}  ·  "
                                   f"pagado {m['pagado']}  ·  saldo pendiente {m['saldo']}")

    # --------------------------------------------------------------- acciones
    def _FJPP_requerir_estudiante(self) -> dict | None:
        if not self.estudiante:
            messagebox.showinfo("Seleccione un estudiante",
                                "Elija un estudiante de la lista de la izquierda.", parent=self)
        return self.estudiante

    def FJPP_matricular(self) -> None:
        estudiante = self._FJPP_requerir_estudiante()
        if not estudiante:
            return
        cursos = self.ctx.cursos.FJPP_listar()
        if not cursos:
            messagebox.showinfo("Sin cursos", "No hay cursos activos. Cree uno en la página Cursos.",
                                parent=self)
            return
        etiquetas = {f"{c['codigo']} — {c['nombre']} ({FJPP_formatear(c['precio_centimos'])})": c for c in cursos}

        def FJPP_guardar(d):
            curso = etiquetas[d["curso"]]
            ok, _ = FJPP_ejecutar_seguro(self, self.ctx.matriculas.FJPP_matricular, estudiante["id"],
                                    curso["id"], d["monto"] or None)
            if ok:
                self._FJPP_cargar_matriculas()
            return ok

        FJPP_Formulario(self, "Matricular en un curso", [
            ("curso", "Curso", list(etiquetas)),
            ("monto", "Monto (vacío = precio del curso)"),
        ], FJPP_guardar, texto_ok="Matricular",
            mensaje=f"Estudiante: {estudiante['apellidos']}, {estudiante['nombres']}")

    def _FJPP_cambiar(self, nuevo_estado: str) -> None:
        m = self.matriculas.FJPP_requerir(self, "Seleccione la matrícula.")
        if not m:
            return
        accion = "completada" if nuevo_estado == COMPLETADA else "retirada"
        if not messagebox.askyesno("Confirmar", f"¿Marcar {m['curso_codigo']} como {accion}?\n"
                                                "Este cambio no se puede deshacer.", parent=self):
            return
        ok, _ = FJPP_ejecutar_seguro(self, self.ctx.matriculas.FJPP_cambiar_estado, m["id"], nuevo_estado)
        if ok:
            self._FJPP_cargar_matriculas()

    def FJPP_solicitar_certificado(self) -> None:
        m = self.matriculas.FJPP_requerir(self, "Seleccione la matrícula del certificado.")
        if not m:
            return
        ok, cert = FJPP_ejecutar_seguro(self, self.ctx.certificados.FJPP_solicitar, m["id"])
        if ok:
            messagebox.showinfo("Certificado solicitado",
                                f"Código {cert['codigo']}.\nQueda pendiente de firma.", parent=self)
            self._FJPP_cargar_matriculas()

    def FJPP_registrar_pago(self) -> None:
        m = self.matriculas.FJPP_requerir(self, "Seleccione la matrícula a la que se aplicará el pago.")
        if not m:
            return

        def FJPP_guardar(d):
            ok, pago = FJPP_ejecutar_seguro(self, self.ctx.pagos.FJPP_registrar, m["id"], d["monto"],
                                       d["metodo"], d["referencia"])
            if ok:
                self._FJPP_cargar_matriculas()
                messagebox.showinfo("Pago registrado", f"Recibo {pago['nro_recibo']}", parent=self)
            return ok

        FJPP_Formulario(self, "Registrar pago", [
            ("monto", f"Monto ({config.MONEDA})"),
            ("metodo", "Método", list(config.METODOS_PAGO)),
            ("referencia", "Referencia / N° operación"),
        ], FJPP_guardar, texto_ok="Registrar pago",
            valores={"monto": f"{max(m['saldo_centimos'], 0) / 100:.2f}"},
            mensaje=f"{m['curso_codigo']} — saldo pendiente {m['saldo']}")

    def FJPP_anular_pago(self) -> None:
        pago = self.pagos.FJPP_requerir(self, "Seleccione el pago que desea anular.")
        if not pago:
            return
        if pago["anulado"]:
            messagebox.showinfo("Pago anulado", "Ese pago ya está anulado.", parent=self)
            return

        def FJPP_guardar(d):
            if not messagebox.askyesno("Confirmar anulación",
                                       f"¿Anular el recibo {pago['nro_recibo']} por {pago['monto']}?",
                                       parent=self):
                return False
            ok, _ = FJPP_ejecutar_seguro(self, self.ctx.pagos.FJPP_anular, pago["id"], d["motivo"])
            if ok:
                self._FJPP_cargar_matriculas()
            return ok

        FJPP_Formulario(self, "Anular pago", [("motivo", "Motivo de la anulación")], FJPP_guardar,
                   texto_ok="Anular pago", mensaje=f"Recibo {pago['nro_recibo']} — {pago['monto']}")
