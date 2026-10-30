"""Ventana principal: barra lateral de navegación + encabezado + página activa."""
from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import ttk

from contexto import FJPP_Contexto
from ui.gui import tema
from ui.gui.certificados import FJPP_PestanaCertificados
from ui.gui.cursos import FJPP_PestanaCursos
from ui.gui.estudiantes import FJPP_PestanaEstudiantes
from ui.gui.matriculas import FJPP_PestanaMatriculas
from ui.gui.resumen import FJPP_PestanaResumen

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "octubre", "noviembre", "diciembre"]

# (clave, texto del menú, título de la página, descripción, clase)
PAGINAS = [
    ("resumen", "Resumen", "Resumen general", "Indicadores, cobranza y deudas pendientes", FJPP_PestanaResumen),
    ("estudiantes", "Estudiantes", "Estudiantes", "Registro y datos de contacto", FJPP_PestanaEstudiantes),
    ("cursos", "Cursos", "Cursos", "Catálogo, precios y alumnos matriculados", FJPP_PestanaCursos),
    ("matriculas", "Matrículas y pagos", "Matrículas y pagos",
     "Cursos que sigue cada estudiante y sus abonos", FJPP_PestanaMatriculas),
    ("certificados", "Certificados", "Certificados", "Seguimiento desde la solicitud hasta el PDF firmado",
     FJPP_PestanaCertificados),
]


def FJPP_fecha_larga(fecha: datetime) -> str:
    return f"{DIAS[fecha.weekday()]}, {fecha.day} de {MESES[fecha.month - 1]} de {fecha.year}"


class FJPP_VentanaPrincipal(tk.Tk):
    def __init__(self, ctx: FJPP_Contexto):
        super().__init__()
        self.ctx = ctx
        self.title("Sistema académico — Pagos, cursos y certificados")
        self.geometry("1280x780")
        self.minsize(1040, 640)
        tema.FJPP_aplicar(self)

        # ---- barra lateral
        lateral = tk.Frame(self, bg=tema.SIDEBAR, width=232)
        lateral.pack(side="left", fill="y")
        lateral.pack_propagate(False)
        ttk.Label(lateral, text="Sistema Académico", style="Marca.TLabel").pack(
            anchor="w", padx=20, pady=(26, 0))
        ttk.Label(lateral, text="Pagos · Cursos · Certificados", style="MarcaSub.TLabel").pack(
            anchor="w", padx=20, pady=(2, 22))
        tk.Frame(lateral, height=1, bg="#2b3a5c").pack(fill="x", padx=16, pady=(0, 12))

        self._nav: dict[str, tuple[tk.Frame, ttk.Button]] = {}
        for i, (clave, texto, *_resto) in enumerate(PAGINAS, start=1):
            fila = tk.Frame(lateral, bg=tema.SIDEBAR)
            fila.pack(fill="x", pady=1)
            marca = tk.Frame(fila, width=4, bg=tema.SIDEBAR)
            marca.pack(side="left", fill="y")
            FJPP_boton = ttk.Button(fila, text=texto, style="Nav.TButton", cursor="hand2",
                               command=lambda c=clave: self.FJPP_mostrar(c))
            FJPP_boton.pack(side="left", fill="x", expand=True)
            self._nav[clave] = (marca, FJPP_boton)
            self.bind(f"<Control-Key-{i}>", lambda _e, c=clave: self.FJPP_mostrar(c))

        ttk.Label(lateral, text=FJPP_fecha_larga(datetime.now()), style="MarcaSub.TLabel",
                  wraplength=190).pack(side="bottom", anchor="w", padx=20, pady=(0, 18))
        tk.Label(lateral, text="Atajos: Ctrl + 1…5", bg=tema.SIDEBAR, fg="#7c8aa8",
                 font=tema.F["pequena"]).pack(side="bottom", anchor="w", padx=20, pady=(0, 4))

        # ---- zona principal
        principal = ttk.Frame(self)
        principal.pack(side="left", fill="both", expand=True)
        cabecera = ttk.Frame(principal, padding=(28, 22, 28, 12))
        cabecera.pack(fill="x")
        self.titulo = ttk.Label(cabecera, style="Titulo.TLabel")
        self.titulo.pack(anchor="w")
        self.subtitulo = ttk.Label(cabecera, style="Sub.TLabel")
        self.subtitulo.pack(anchor="w", pady=(2, 0))
        self.contenido = ttk.Frame(principal, padding=(28, 4, 28, 24))
        self.contenido.pack(fill="both", expand=True)

        self.paginas: dict[str, ttk.Frame] = {}
        self._info: dict[str, tuple[str, str]] = {}
        for clave, _texto, titulo, descripcion, clase in PAGINAS:
            self.paginas[clave] = clase(self.contenido, ctx)
            self._info[clave] = (titulo, descripcion)
        self.pestanas = [(PAGINAS[i][1], self.paginas[PAGINAS[i][0]]) for i in range(len(PAGINAS))]
        self._actual: str | None = None
        self.FJPP_mostrar("resumen")

    def FJPP_mostrar(self, clave: str) -> None:
        if self._actual:
            self.paginas[self._actual].pack_forget()
            marca, FJPP_boton = self._nav[self._actual]
            marca.config(bg=tema.SIDEBAR)
            FJPP_boton.config(style="Nav.TButton")
        self._actual = clave
        marca, FJPP_boton = self._nav[clave]
        marca.config(bg=tema.ACENTO)
        FJPP_boton.config(style="NavActive.TButton")
        self.titulo.config(text=self._info[clave][0])
        self.subtitulo.config(text=self._info[clave][1])
        pagina = self.paginas[clave]
        pagina.pack(fill="both", expand=True)
        pagina.FJPP_refrescar()  # otra página pudo haber cambiado los datos

    def FJPP_pestana_actual(self):
        return self.paginas[self._actual]


def FJPP_lanzar(ctx: FJPP_Contexto) -> None:
    FJPP_VentanaPrincipal(ctx).mainloop()
