"""Página de cursos: catálogo, precios y alumnos matriculados."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from core.dinero import FJPP_formatear
from ui.gui.base import (FJPP_Formulario, FJPP_Pestana, FJPP_Tabla, FJPP_Tarjeta, FJPP_barra_botones, FJPP_ejecutar_seguro)


class FJPP_PestanaCursos(FJPP_Pestana):
    def __init__(self, parent, ctx):
        super().__init__(parent, ctx)
        self.inactivos = tk.BooleanVar(value=False)

        panel = ttk.PanedWindow(self, orient="vertical")
        panel.pack(fill="both", expand=True)

        arriba = ttk.Frame(panel)
        cab = ttk.Frame(arriba)
        cab.pack(fill="x", pady=(0, 8))
        FJPP_barra_botones(cab, [("+ Nuevo curso", self.FJPP_nuevo, "primary"),
                            ("Cambiar precio", self.FJPP_cambiar_precio),
                            ("Desactivar", self.FJPP_desactivar, "danger")]).pack(side="left")
        ttk.Checkbutton(cab, text="Incluir inactivos", variable=self.inactivos,
                        command=self.FJPP_refrescar).pack(side="right")
        t1 = FJPP_Tarjeta(arriba, relleno=0)
        t1.pack(fill="both", expand=True)
        self.FJPP_tabla = FJPP_Tabla(t1.cuerpo, [
            ("codigo", "Código", 90), ("nombre", "Curso", 280), ("horas", "Horas", 60, "center"),
            ("precio", "Precio", 110, "e"), ("estado", "Estado", 90),
        ], alto=7, al_seleccionar=lambda _f: self._FJPP_cargar_alumnos())
        self.FJPP_tabla.pack(fill="both", expand=True)
        self.FJPP_tabla.tree.tag_configure("inactivo", foreground="#94a3b8")
        panel.add(arriba, weight=3)

        abajo = ttk.Frame(panel)
        ttk.Label(abajo, text="Alumnos matriculados en el curso seleccionado",
                  style="Muted.TLabel").pack(anchor="w", pady=(10, 6))
        t2 = FJPP_Tarjeta(abajo, relleno=0)
        t2.pack(fill="both", expand=True)
        self.alumnos = FJPP_Tabla(t2.cuerpo, [
            ("dni", "DNI", 90), ("estudiante", "Estudiante", 250), ("estado", "Estado", 110),
            ("monto", "Monto", 100, "e"), ("pagado", "Pagado", 100, "e"), ("saldo", "Saldo", 100, "e"),
        ], alto=5)
        self.alumnos.pack(fill="both", expand=True)
        panel.add(abajo, weight=2)

    def FJPP_refrescar(self) -> None:
        ok, filas = FJPP_ejecutar_seguro(self, self.ctx.cursos.FJPP_listar, solo_activos=not self.inactivos.get())
        if ok:
            for f in filas:
                f["precio"] = FJPP_formatear(f["precio_centimos"])
                f["estado"] = "Activo" if f["activo"] else "Inactivo"
            self.FJPP_tabla.FJPP_cargar(filas, etiqueta=lambda f: "" if f["activo"] else "inactivo")
            self._FJPP_cargar_alumnos()

    def _FJPP_cargar_alumnos(self) -> None:
        curso = self.FJPP_tabla.FJPP_seleccionada()
        if not curso:
            self.alumnos.FJPP_cargar([])
            return
        ok, filas = FJPP_ejecutar_seguro(self, self.ctx.matriculas.FJPP_listar_por_curso, curso["id"])
        if ok:
            for m in filas:
                m["monto"] = FJPP_formatear(m["monto_centimos"])
                m["pagado"] = FJPP_formatear(m["pagado_centimos"])
                m["saldo"] = FJPP_formatear(m["saldo_centimos"])
            self.alumnos.FJPP_cargar(filas)

    def FJPP_nuevo(self) -> None:
        def FJPP_guardar(d):
            ok, _ = FJPP_ejecutar_seguro(self, self.ctx.cursos.FJPP_crear, d["codigo"], d["nombre"],
                                    d["horas"], d["precio"])
            if ok:
                self.FJPP_refrescar()
            return ok

        FJPP_Formulario(self, "Nuevo curso", [
            ("codigo", "Código (ej. EXC-01)"), ("nombre", "Nombre del curso"),
            ("horas", "Horas"), ("precio", "Precio"),
        ], FJPP_guardar, texto_ok="Crear curso")

    def FJPP_cambiar_precio(self) -> None:
        curso = self.FJPP_tabla.FJPP_requerir(self, "Seleccione un curso.")
        if not curso:
            return

        def FJPP_guardar(d):
            ok, _ = FJPP_ejecutar_seguro(self, self.ctx.cursos.FJPP_cambiar_precio, curso["id"], d["precio"])
            if ok:
                self.FJPP_refrescar()
            return ok

        FJPP_Formulario(self, f"Cambiar precio de {curso['codigo']}", [("precio", "Nuevo precio")],
                   FJPP_guardar, valores={"precio": f"{curso['precio_centimos'] / 100:.2f}"},
                   mensaje="El cambio no afecta a las matrículas ya registradas.")

    def FJPP_desactivar(self) -> None:
        curso = self.FJPP_tabla.FJPP_requerir(self, "Seleccione un curso.")
        if not curso:
            return
        if not messagebox.askyesno("Desactivar curso",
                                   f"¿Desactivar {curso['codigo']}? Ya no admitirá nuevas matrículas.",
                                   parent=self):
            return
        ok, _ = FJPP_ejecutar_seguro(self, self.ctx.cursos.FJPP_desactivar, curso["id"])
        if ok:
            self.FJPP_refrescar()
