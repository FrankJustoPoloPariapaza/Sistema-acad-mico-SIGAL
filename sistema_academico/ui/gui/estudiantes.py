"""Página de estudiantes: buscar, registrar, editar y desactivar."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from ui.gui import tema
from ui.gui.base import (FJPP_Formulario, FJPP_Pestana, FJPP_Tabla, FJPP_Tarjeta, FJPP_barra_botones, FJPP_ejecutar_seguro)


class FJPP_PestanaEstudiantes(FJPP_Pestana):
    def __init__(self, parent, ctx):
        super().__init__(parent, ctx)
        self.texto = tk.StringVar()
        self.inactivos = tk.BooleanVar(value=False)

        filtro = ttk.Frame(self)
        filtro.pack(fill="x", pady=(0, 10))
        ttk.Entry(filtro, textvariable=self.texto, width=38).pack(side="left")
        ttk.Label(filtro, text="Buscar por DNI, nombre o apellido", style="Muted.TLabel").pack(
            side="left", padx=10)
        ttk.Checkbutton(filtro, text="Incluir inactivos", variable=self.inactivos,
                        command=self.FJPP_refrescar).pack(side="right")
        self.texto.trace_add("write", lambda *_: self.FJPP_refrescar())

        tarjeta = FJPP_Tarjeta(self, relleno=0)
        tarjeta.pack(fill="both", expand=True)
        self.FJPP_tabla = FJPP_Tabla(tarjeta.cuerpo, [
            ("dni", "DNI", 90), ("apellidos", "Apellidos", 200), ("nombres", "Nombres", 160),
            ("email", "Correo", 210), ("telefono", "Teléfono", 110), ("estado", "Estado", 80),
        ], alto=16)
        self.FJPP_tabla.pack(fill="both", expand=True)
        self.FJPP_tabla.tree.tag_configure("inactivo", foreground="#94a3b8")
        self.FJPP_tabla.tree.bind("<Double-1>", lambda _e: self.FJPP_editar())

        FJPP_barra_botones(self, [("+ Nuevo estudiante", self.FJPP_nuevo, "primary"),
                             ("Editar", self.FJPP_editar),
                             ("Desactivar", self.FJPP_desactivar, "danger")]).pack(anchor="w", pady=(12, 0))

    def FJPP_refrescar(self) -> None:
        ok, filas = FJPP_ejecutar_seguro(self, self.ctx.estudiantes.FJPP_buscar, self.texto.get().strip(),
                                    solo_activos=not self.inactivos.get())
        if ok:
            for f in filas:
                f["estado"] = "Activo" if f["activo"] else "Inactivo"
            self.FJPP_tabla.FJPP_cargar(filas, etiqueta=lambda f: "" if f["activo"] else "inactivo")

    def FJPP_nuevo(self) -> None:
        def FJPP_guardar(d):
            ok, _ = FJPP_ejecutar_seguro(self, self.ctx.estudiantes.FJPP_crear, d["dni"], d["nombres"],
                                    d["apellidos"], d["email"], d["telefono"])
            if ok:
                self.FJPP_refrescar()
            return ok

        FJPP_Formulario(self, "Nuevo estudiante", [
            ("dni", "DNI (8 dígitos)"), ("nombres", "Nombres"), ("apellidos", "Apellidos"),
            ("email", "Correo (opcional)"), ("telefono", "Teléfono (opcional)"),
        ], FJPP_guardar, texto_ok="Registrar")

    def FJPP_editar(self) -> None:
        fila = self.FJPP_tabla.FJPP_requerir(self, "Seleccione el estudiante que desea editar.")
        if not fila:
            return

        def FJPP_guardar(d):
            ok, _ = FJPP_ejecutar_seguro(self, self.ctx.estudiantes.FJPP_actualizar, fila["id"],
                                    nombres=d["nombres"], apellidos=d["apellidos"],
                                    email=d["email"], telefono=d["telefono"])
            if ok:
                self.FJPP_refrescar()
            return ok

        FJPP_Formulario(self, "Editar estudiante", [
            ("nombres", "Nombres"), ("apellidos", "Apellidos"),
            ("email", "Correo"), ("telefono", "Teléfono"),
        ], FJPP_guardar, valores=fila, mensaje=f"DNI {fila['dni']}")

    def FJPP_desactivar(self) -> None:
        fila = self.FJPP_tabla.FJPP_requerir(self, "Seleccione el estudiante que desea desactivar.")
        if not fila:
            return
        if not messagebox.askyesno("Desactivar estudiante",
                                   f"¿Desactivar a {fila['apellidos']}, {fila['nombres']}?\n"
                                   "Su historial se conserva.", parent=self):
            return
        ok, _ = FJPP_ejecutar_seguro(self, self.ctx.estudiantes.FJPP_desactivar, fila["id"])
        if ok:
            self.FJPP_refrescar()
