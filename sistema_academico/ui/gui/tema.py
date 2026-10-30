"""Tema visual de la aplicación: paleta, fuentes y estilos ttk.

Solo usa Tkinter/ttk (sin bibliotecas externas), de modo que el .exe sigue siendo liviano.
Se usa el tema 'clam' en todos los sistemas para que el aspecto sea el mismo en Windows,
Mac y Linux (el tema nativo de Windows ignora la mayoría de los colores).
"""
from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

# ---- paleta
BG = "#f3f5f9"            # fondo de las páginas
PANEL = "#ffffff"         # tarjetas
BORDE = "#e2e8f0"
TEXTO = "#1e293b"
MUTED = "#64748b"
SIDEBAR = "#16213a"
SIDEBAR_HOVER = "#243252"
SIDEBAR_TEXTO = "#cbd5e1"
ACENTO = "#2563eb"
ACENTO_OSC = "#1d4ed8"
ACENTO_SUAVE = "#dbeafe"
OK = "#15803d"
AVISO = "#b45309"
PELIGRO = "#b91c1c"
FILA_ALT = "#f8fafc"
CABECERA_TABLA = "#eef2f7"

F: dict[str, tkfont.Font] = {}   # fuentes con nombre, se crean en aplicar()


def _FJPP_familia() -> str:
    disponibles = set(tkfont.families())
    for nombre in ("Segoe UI", "SF Pro Text", "Helvetica Neue", "Inter", "Roboto", "Ubuntu",
                   "DejaVu Sans", "Arial"):
        if nombre in disponibles:
            return nombre
    return tkfont.nametofont("TkDefaultFont").actual("family")


def FJPP_aplicar(raiz: tk.Tk) -> None:
    familia = _FJPP_familia()
    for nombre in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkFixedFont"):
        try:
            tkfont.nametofont(nombre).configure(family=familia, size=10)
        except tk.TclError:
            pass

    def FJPP_fuente(tam: int, negrita: bool = False) -> tkfont.Font:
        return tkfont.Font(family=familia, size=tam, weight="bold" if negrita else "normal")

    F.update(normal=FJPP_fuente(10), negrita=FJPP_fuente(10, True), pequena=FJPP_fuente(9), titulo=FJPP_fuente(19, True),
             subtitulo=FJPP_fuente(10), card=FJPP_fuente(11, True), kpi=FJPP_fuente(17, True), marca=FJPP_fuente(14, True),
             nav=FJPP_fuente(11), nav_activo=FJPP_fuente(11, True))

    raiz.configure(bg=BG)
    raiz.option_add("*TCombobox*Listbox.background", PANEL)
    raiz.option_add("*TCombobox*Listbox.foreground", TEXTO)
    raiz.option_add("*TCombobox*Listbox.selectBackground", ACENTO_SUAVE)
    raiz.option_add("*TCombobox*Listbox.selectForeground", TEXTO)
    raiz.option_add("*TCombobox*Listbox.font", F["normal"])

    e = ttk.Style(raiz)
    e.theme_use("clam")
    e.configure(".", background=BG, foreground=TEXTO, font=F["normal"], bordercolor=BORDE,
                focuscolor=BG, troughcolor=BORDE)

    # ---- contenedores y etiquetas
    e.configure("TFrame", background=BG)
    e.configure("Card.TFrame", background=PANEL)
    e.configure("TLabel", background=BG, foreground=TEXTO)
    e.configure("Card.TLabel", background=PANEL)
    e.configure("Titulo.TLabel", font=F["titulo"])
    e.configure("Sub.TLabel", foreground=MUTED, font=F["subtitulo"])
    e.configure("Muted.TLabel", foreground=MUTED)
    e.configure("CardMuted.TLabel", background=PANEL, foreground=MUTED)
    e.configure("CardTitulo.TLabel", background=PANEL, font=F["card"])
    e.configure("Campo.TLabel", background=PANEL, foreground=MUTED, font=F["pequena"])
    e.configure("Kpi.TLabel", background=PANEL, font=F["kpi"])
    e.configure("KpiTit.TLabel", background=PANEL, foreground=MUTED, font=F["pequena"])
    e.configure("Marca.TLabel", background=SIDEBAR, foreground="#ffffff", font=F["marca"])
    e.configure("MarcaSub.TLabel", background=SIDEBAR, foreground=SIDEBAR_TEXTO, font=F["pequena"])
    e.configure("TCheckbutton", background=BG, focuscolor=BG)
    e.map("TCheckbutton", background=[("active", BG)])
    e.configure("Card.TCheckbutton", background=PANEL)
    e.map("Card.TCheckbutton", background=[("active", PANEL)])

    # ---- botones
    def FJPP_boton(nombre, fondo, texto, hover, borde=None, fuente_=None):
        borde = borde or fondo
        e.configure(nombre, background=fondo, foreground=texto, bordercolor=borde, lightcolor=fondo,
                    darkcolor=fondo, focusthickness=0, focuscolor=fondo, padding=(14, 7),
                    relief="solid", borderwidth=1, font=fuente_ or F["negrita"])
        e.map(nombre, background=[("pressed", hover), ("active", hover)],
              lightcolor=[("pressed", hover), ("active", hover)],
              darkcolor=[("pressed", hover), ("active", hover)],
              bordercolor=[("active", borde if borde != fondo else hover)])

    FJPP_boton("Primary.TButton", ACENTO, "#ffffff", ACENTO_OSC)
    FJPP_boton("Secondary.TButton", PANEL, TEXTO, "#eef2f7", borde="#94a3b8")
    FJPP_boton("Danger.TButton", PANEL, PELIGRO, "#fef2f2", borde="#f87171")
    FJPP_boton("Nav.TButton", SIDEBAR, SIDEBAR_TEXTO, SIDEBAR_HOVER, fuente_=F["nav"])
    FJPP_boton("NavActive.TButton", SIDEBAR_HOVER, "#ffffff", SIDEBAR_HOVER, fuente_=F["nav_activo"])
    for nav in ("Nav.TButton", "NavActive.TButton"):
        e.configure(nav, anchor="w", padding=(16, 11))

    # ---- campos de texto
    campo = dict(fieldbackground="#ffffff", foreground=TEXTO, bordercolor="#cbd5e1",
                 lightcolor="#ffffff", darkcolor="#ffffff", padding=7, insertcolor=TEXTO)
    e.configure("TEntry", **campo)
    e.configure("TCombobox", arrowcolor=MUTED, background=PANEL, **campo)
    foco = [("focus", ACENTO)]
    e.map("TEntry", bordercolor=foco, lightcolor=foco, darkcolor=foco)
    e.map("TCombobox", bordercolor=foco, lightcolor=foco, darkcolor=foco,
          fieldbackground=[("readonly", "#ffffff")], foreground=[("readonly", TEXTO)],
          selectbackground=[("readonly", "#ffffff")], selectforeground=[("readonly", TEXTO)])

    # ---- tablas
    e.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXTO,
                rowheight=30, borderwidth=0, relief="flat", font=F["normal"])
    e.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    e.map("Treeview", background=[("selected", ACENTO_SUAVE)], foreground=[("selected", TEXTO)])
    e.configure("Treeview.Heading", background=CABECERA_TABLA, foreground=MUTED, relief="flat",
                font=F["negrita"], padding=(8, 8), borderwidth=0)
    e.map("Treeview.Heading", background=[("active", "#e2e8f0")])

    # ---- barras de desplazamiento delgadas, sin flechas
    e.layout("Vertical.TScrollbar", [("Vertical.Scrollbar.trough", {
        "sticky": "ns", "children": [("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
    e.configure("Vertical.TScrollbar", background="#cbd5e1", troughcolor=PANEL, bordercolor=PANEL,
                lightcolor="#cbd5e1", darkcolor="#cbd5e1", width=9, relief="flat")
    e.map("Vertical.TScrollbar", background=[("active", "#94a3b8")],
          lightcolor=[("active", "#94a3b8")], darkcolor=[("active", "#94a3b8")])

    e.configure("TPanedwindow", background=BG)
    e.configure("Sash", sashthickness=8, background=BG, gripcount=0)
