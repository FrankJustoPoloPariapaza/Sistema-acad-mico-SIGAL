"""Piezas reutilizables de la interfaz: tarjeta, tabla, botones, formulario y errores."""
from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from core.excepciones import FJPP_ErrorDeNegocio
from ui.gui import tema


def FJPP_mostrar_error(parent, error: Exception) -> None:
    if isinstance(error, FJPP_ErrorDeNegocio):
        messagebox.showwarning("No se pudo completar", str(error), parent=parent)
    else:
        messagebox.showerror("Error inesperado", f"{type(error).__name__}: {error}", parent=parent)


def FJPP_ejecutar_seguro(parent, funcion, *args, **kwargs):
    """Ejecuta una operación y muestra los errores en un cuadro de diálogo.

    Devuelve (True, resultado) si salió bien, o (False, None) si falló.
    """
    try:
        return True, funcion(*args, **kwargs)
    except Exception as error:  # un error no debe cerrar el programa
        FJPP_mostrar_error(parent, error)
    return False, None


def FJPP_abrir_archivo(ruta: Path) -> None:
    """Abre un archivo con el programa predeterminado del sistema."""
    if sys.platform.startswith("win"):
        os.startfile(str(ruta))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(ruta)])
    else:
        subprocess.Popen(["xdg-open", str(ruta)])


class FJPP_Tarjeta(tk.Frame):
    """Panel blanco con borde fino y, opcionalmente, título y franja de color a la izquierda."""

    def __init__(self, parent, titulo: str = "", acento: str | None = None, relleno: int = 14):
        super().__init__(parent, bg=tema.BORDE)
        if acento:
            tk.Frame(self, width=4, bg=acento).pack(side="left", fill="y", padx=(1, 0), pady=1)
        self.cuerpo = ttk.Frame(self, style="Card.TFrame", padding=relleno)
        self.cuerpo.pack(fill="both", expand=True, padx=1, pady=1)
        if titulo:
            ttk.Label(self.cuerpo, text=titulo, style="CardTitulo.TLabel").pack(anchor="w", pady=(0, 8))


class FJPP_Tabla(ttk.Frame):
    """Treeview con filas alternadas y barra de desplazamiento. Cada fila es un dict."""

    def __init__(self, parent, columnas, alto: int = 10, al_seleccionar=None, clave_id: str = "id"):
        """columnas: lista de (clave, titulo, ancho) o (clave, titulo, ancho, anclaje)."""
        super().__init__(parent, style="Card.TFrame")
        self._claves = [c[0] for c in columnas]
        self._clave_id = clave_id
        self._filas: dict[str, dict] = {}
        self.tree = ttk.Treeview(self, columns=self._claves, show="headings",
                                 height=alto, selectmode="browse")
        for clave, titulo, ancho, *resto in columnas:
            self.tree.heading(clave, text=titulo, anchor=resto[0] if resto else "w")
            self.tree.column(clave, width=ancho, minwidth=40,
                             anchor=resto[0] if resto else "w", stretch=True)
        barra = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)

        def FJPP_desplazar(inicio, fin):  # la barra solo aparece cuando hay más filas de las visibles
            barra.set(inicio, fin)
            if float(inicio) <= 0.0 and float(fin) >= 1.0:
                barra.grid_remove()
            else:
                barra.grid()

        self.tree.configure(yscrollcommand=FJPP_desplazar)
        self.tree.grid(row=0, column=0, sticky="nsew")
        barra.grid(row=0, column=1, sticky="ns")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.tree.tag_configure("par", background=tema.PANEL)
        self.tree.tag_configure("impar", background=tema.FILA_ALT)
        if al_seleccionar:
            self.tree.bind("<<TreeviewSelect>>", lambda _e: al_seleccionar(self.FJPP_seleccionada()))

    def FJPP_cargar(self, filas: list[dict], etiqueta=None) -> None:
        """Reemplaza el contenido conservando la selección si la fila sigue existiendo."""
        anterior = self.tree.selection()
        self.tree.delete(*self.tree.get_children())
        self._filas = {}
        for posicion, fila in enumerate(filas):
            iid = str(fila.get(self._clave_id, posicion))
            self._filas[iid] = fila
            valores = ["" if fila.get(c) is None else fila.get(c) for c in self._claves]
            etiquetas = ["impar" if posicion % 2 else "par"]
            if etiqueta and etiqueta(fila):
                etiquetas.append(etiqueta(fila))
            self.tree.insert("", "end", iid=iid, values=valores, tags=tuple(etiquetas))
        if anterior and anterior[0] in self._filas:
            self.tree.selection_set(anterior[0])
            self.tree.see(anterior[0])

    def FJPP_seleccionada(self) -> dict | None:
        seleccion = self.tree.selection()
        return self._filas.get(seleccion[0]) if seleccion else None

    def FJPP_requerir(self, parent, mensaje: str) -> dict | None:
        """Devuelve la fila seleccionada o avisa al usuario que debe elegir una."""
        fila = self.FJPP_seleccionada()
        if fila is None:
            messagebox.showinfo("Seleccione una fila", mensaje, parent=parent)
        return fila


def FJPP_barra_botones(parent, botones, tarjeta: bool = False) -> ttk.Frame:
    """botones: lista de (texto, comando) o (texto, comando, estilo).

    estilo: 'primary' (acción principal), 'secondary' (por defecto) o 'danger'.
    """
    marco = ttk.Frame(parent, style="Card.TFrame" if tarjeta else "TFrame")
    estilos = {"primary": "Primary.TButton", "secondary": "Secondary.TButton",
               "danger": "Danger.TButton"}
    for texto, comando, *resto in botones:
        FJPP_boton = ttk.Button(marco, text=texto, command=comando, cursor="hand2",
                           style=estilos[resto[0] if resto else "secondary"])
        FJPP_boton.pack(side="left", padx=(0, 8))
    return marco


class FJPP_Formulario(tk.Toplevel):
    """Ventana modal de captura de datos.

    campos: lista de (clave, etiqueta) o (clave, etiqueta, [opciones]) para una lista desplegable.
    al_aceptar(datos) debe devolver True si todo salió bien; si no, el formulario
    queda abierto con lo escrito para que el usuario corrija.
    """

    def __init__(self, parent, titulo: str, campos, al_aceptar, valores: dict | None = None,
                 texto_ok: str = "Guardar", mensaje: str = ""):
        super().__init__(parent, bg=tema.PANEL)
        self.title(titulo)
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self._al_aceptar = al_aceptar
        self._vars: dict[str, tk.StringVar] = {}
        valores = valores or {}

        tk.Frame(self, height=4, bg=tema.ACENTO).pack(fill="x")
        marco = ttk.Frame(self, style="Card.TFrame", padding=(22, 16, 22, 18))
        marco.pack(fill="both", expand=True)
        marco.columnconfigure(0, weight=1)
        ttk.Label(marco, text=titulo, style="CardTitulo.TLabel",
                  font=tema.F["marca"]).grid(row=0, column=0, sticky="w")
        fila = 1
        if mensaje:
            ttk.Label(marco, text=mensaje, style="CardMuted.TLabel", wraplength=380,
                      justify="left").grid(row=fila, column=0, sticky="w", pady=(4, 0))
            fila += 1
        ttk.Frame(marco, style="Card.TFrame", height=8).grid(row=fila, column=0)
        fila += 1

        primero = None
        for campo in campos:
            clave, etiqueta, *resto = campo
            var = tk.StringVar(value=str(valores.get(clave, "") or ""))
            self._vars[clave] = var
            ttk.Label(marco, text=etiqueta.upper(), style="Campo.TLabel").grid(
                row=fila, column=0, sticky="w", pady=(8, 2))
            if resto:
                widget = ttk.Combobox(marco, textvariable=var, values=resto[0],
                                      state="readonly", width=44)
                if not var.get() and resto[0]:
                    var.set(resto[0][0])
            else:
                widget = ttk.Entry(marco, textvariable=var, width=46)
            widget.grid(row=fila + 1, column=0, sticky="ew")
            primero = primero or widget
            fila += 2

        botones = ttk.Frame(marco, style="Card.TFrame")
        botones.grid(row=fila, column=0, sticky="e", pady=(20, 0))
        ttk.Button(botones, text="Cancelar", style="Secondary.TButton", cursor="hand2",
                   command=self.destroy).pack(side="left", padx=(0, 8))
        ttk.Button(botones, text=texto_ok, style="Primary.TButton", cursor="hand2",
                   command=self._FJPP_aceptar).pack(side="left")

        self.bind("<Return>", lambda _e: self._FJPP_aceptar())
        self.bind("<Escape>", lambda _e: self.destroy())
        self.update_idletasks()
        padre = parent.winfo_toplevel()
        x = padre.winfo_rootx() + (padre.winfo_width() - self.winfo_reqwidth()) // 2
        y = padre.winfo_rooty() + (padre.winfo_height() - self.winfo_reqheight()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.grab_set()
        if primero is not None:
            primero.focus_set()

    def datos(self) -> dict[str, str]:
        return {clave: var.get().strip() for clave, var in self._vars.items()}

    def _FJPP_aceptar(self) -> None:
        if self._al_aceptar(self.datos()):
            self.destroy()


class FJPP_Pestana(ttk.Frame):
    """Base de cada página: guarda el contexto y obliga a implementar refrescar()."""

    def __init__(self, parent, ctx):
        super().__init__(parent)
        self.ctx = ctx

    def FJPP_refrescar(self) -> None:
        raise NotImplementedError
