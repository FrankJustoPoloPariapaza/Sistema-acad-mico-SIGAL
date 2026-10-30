"""Página de resumen: indicadores, cobranza, estado de certificados y deudores."""
from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

from core.dinero import FJPP_formatear
from modulos.certificados import ENVIADO, ESTADOS, FIRMADO, PENDIENTE
from modulos.reportes import FJPP_exportar_csv
from ui.gui import tema
from ui.gui.base import FJPP_Pestana, FJPP_Tabla, FJPP_Tarjeta, FJPP_barra_botones, FJPP_ejecutar_seguro
from ui.gui.certificados import COLOR_ESTADO, TEXTO_ESTADO


class FJPP_BarraSegmentada(tk.Canvas):
    """Barra horizontal dividida en segmentos proporcionales (se redibuja al cambiar de tamaño)."""

    def __init__(self, parent, alto: int = 12):
        super().__init__(parent, height=alto, bg=tema.PANEL, highlightthickness=0)
        self._segmentos: list[tuple[float, str]] = []
        self.bind("<Configure>", lambda _e: self._FJPP_dibujar())

    def FJPP_poner(self, segmentos: list[tuple[float, str]]) -> None:
        self._segmentos = segmentos
        self._FJPP_dibujar()

    def _FJPP_dibujar(self) -> None:
        self.delete("all")
        ancho, alto = self.winfo_width(), self.winfo_height()
        self.create_rectangle(0, 0, ancho, alto, fill=tema.BORDE, outline="")
        total = sum(v for v, _ in self._segmentos)
        if total <= 0:
            return
        x = 0.0
        for valor, color in self._segmentos:
            if valor <= 0:
                continue
            fin = x + ancho * valor / total
            self.create_rectangle(x, 0, fin, alto, fill=color, outline="")
            x = fin


class FJPP_PestanaResumen(FJPP_Pestana):
    def __init__(self, parent, ctx):
        super().__init__(parent, ctx)
        self.valores: dict[str, ttk.Label] = {}
        self._deudores: list[dict] = []

        # ---- indicadores
        fila = ttk.Frame(self)
        fila.pack(fill="x")
        indicadores = [
            ("estudiantes", "ESTUDIANTES ACTIVOS", tema.ACENTO), ("cursos", "CURSOS ACTIVOS", "#7c3aed"),
            ("en_curso", "MATRÍCULAS EN CURSO", "#0891b2"), ("facturado", "FACTURADO", tema.MUTED),
            ("recaudado", "RECAUDADO", tema.OK), ("por_cobrar", "POR COBRAR", tema.PELIGRO),
        ]
        for i, (clave, texto, color) in enumerate(indicadores):
            tarjeta = FJPP_Tarjeta(fila, acento=color, relleno=12)
            tarjeta.grid(row=i // 3, column=i % 3, sticky="nsew", padx=(0 if i % 3 == 0 else 5, 0 if i % 3 == 2 else 5),
                         pady=(0 if i < 3 else 10, 0))
            ttk.Label(tarjeta.cuerpo, text=texto, style="KpiTit.TLabel").pack(anchor="w")
            etiqueta = ttk.Label(tarjeta.cuerpo, text="—", style="Kpi.TLabel")
            etiqueta.pack(anchor="w", pady=(2, 0))
            self.valores[clave] = etiqueta
            fila.columnconfigure(i % 3, weight=1, uniform="kpi")

        # ---- cobranza y certificados
        medio = ttk.Frame(self)
        medio.pack(fill="x", pady=12)
        medio.columnconfigure(0, weight=1, uniform="m")
        medio.columnconfigure(1, weight=1, uniform="m")

        cobranza = FJPP_Tarjeta(medio, "Cobranza")
        cobranza.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.barra_cobranza = FJPP_BarraSegmentada(cobranza.cuerpo)
        self.barra_cobranza.pack(fill="x", pady=(2, 8))
        self.texto_cobranza = ttk.Label(cobranza.cuerpo, text="", style="CardMuted.TLabel")
        self.texto_cobranza.pack(anchor="w")

        certs = FJPP_Tarjeta(medio, "Certificados")
        certs.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self.barra_certs = FJPP_BarraSegmentada(certs.cuerpo)
        self.barra_certs.pack(fill="x", pady=(2, 8))
        leyenda = ttk.Frame(certs.cuerpo, style="Card.TFrame")
        leyenda.pack(anchor="w")
        self.leyenda: dict[str, ttk.Label] = {}
        for estado in ESTADOS:
            ttk.Label(leyenda, text="●", style="Card.TLabel", foreground=COLOR_ESTADO[estado]).pack(
                side="left")
            etiqueta = ttk.Label(leyenda, text=TEXTO_ESTADO[estado], style="CardMuted.TLabel")
            etiqueta.pack(side="left", padx=(4, 16))
            self.leyenda[estado] = etiqueta

        # ---- deudores
        cab = ttk.Frame(self)
        cab.pack(fill="x", pady=(0, 6))
        ttk.Label(cab, text="Matrículas con saldo pendiente", font=tema.F["card"]).pack(side="left")
        self.total = ttk.Label(cab, text="", font=tema.F["negrita"], foreground=tema.PELIGRO)
        self.total.pack(side="right")
        tarjeta = FJPP_Tarjeta(self, relleno=0)
        tarjeta.pack(fill="both", expand=True)
        self.FJPP_tabla = FJPP_Tabla(tarjeta.cuerpo, [
            ("dni", "DNI", 90), ("estudiante", "Estudiante", 240), ("curso_codigo", "Curso", 80),
            ("estado", "Estado", 100), ("monto", "Monto", 90, "e"),
            ("pagado", "Pagado", 90, "e"), ("saldo", "Saldo", 90, "e"),
        ], alto=5, clave_id="matricula_id")
        self.FJPP_tabla.pack(fill="both", expand=True)
        FJPP_barra_botones(self, [("Actualizar", self.FJPP_refrescar),
                             ("Exportar deudores a CSV", self.FJPP_exportar)]).pack(anchor="w", pady=(12, 0))

    def FJPP_refrescar(self) -> None:
        ok, r = FJPP_ejecutar_seguro(self, self.ctx.reportes.FJPP_resumen)
        if ok:
            v = self.valores
            v["estudiantes"].config(text=str(r["estudiantes_activos"]))
            v["cursos"].config(text=str(r["cursos_activos"]))
            v["en_curso"].config(text=str(r["matriculas_en_curso"]))
            v["facturado"].config(text=FJPP_formatear(r["facturado_centimos"]))
            v["recaudado"].config(text=FJPP_formatear(r["recaudado_centimos"]))
            v["por_cobrar"].config(text=FJPP_formatear(r["por_cobrar_centimos"]))

            facturado, recaudado = r["facturado_centimos"], r["recaudado_centimos"]
            self.barra_cobranza.FJPP_poner([(recaudado, tema.OK), (max(facturado - recaudado, 0), "#fca5a5")])
            pct = (recaudado / facturado * 100) if facturado else 0
            self.texto_cobranza.config(
                text=f"{pct:.0f} % cobrado  ·  {FJPP_formatear(recaudado)} de {FJPP_formatear(facturado)}")

            cuentas = r["certificados"]
            self.barra_certs.FJPP_poner([(cuentas.get(e, 0), COLOR_ESTADO[e]) for e in (PENDIENTE, ENVIADO, FIRMADO)])
            for estado in ESTADOS:
                self.leyenda[estado].config(text=f"{TEXTO_ESTADO[estado]}: {cuentas.get(estado, 0)}")

        ok, filas = FJPP_ejecutar_seguro(self, self.ctx.pagos.FJPP_deudores)
        if ok:
            for d in filas:
                d["monto"] = FJPP_formatear(d["monto_centimos"])
                d["pagado"] = FJPP_formatear(d["pagado_centimos"])
                d["saldo"] = FJPP_formatear(d["saldo_centimos"])
            self._deudores = filas
            self.FJPP_tabla.FJPP_cargar(filas)
            total = sum(d["saldo_centimos"] for d in filas)
            self.total.config(text=f"Total por cobrar: {FJPP_formatear(total)}" if filas else "Sin deudas")

    def FJPP_exportar(self) -> None:
        if not self._deudores:
            messagebox.showinfo("Sin datos", "No hay deudores para exportar.", parent=self)
            return
        ruta = filedialog.asksaveasfilename(
            parent=self, title="Exportar deudores", defaultextension=".csv",
            initialfile=f"deudores_{datetime.now():%Y%m%d}.csv",
            filetypes=[("CSV (Excel)", "*.csv")])
        if not ruta:
            return
        columnas = ["dni", "estudiante", "curso_codigo", "estado", "monto", "pagado", "saldo"]
        ok, destino = FJPP_ejecutar_seguro(self, FJPP_exportar_csv, self._deudores, columnas, ruta)
        if ok:
            messagebox.showinfo("Exportado", f"Archivo guardado en:\n{destino}", parent=self)
