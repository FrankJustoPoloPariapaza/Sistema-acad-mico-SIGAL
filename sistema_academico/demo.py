"""Datos de ejemplo para probar el sistema: python main.py --demo"""
from __future__ import annotations

from contexto import FJPP_Contexto


def FJPP_cargar_demo(ctx: FJPP_Contexto) -> bool:
    """Carga datos de ejemplo solo si la base está vacía. Devuelve True si cargó."""
    if ctx.estudiantes.FJPP_buscar("", solo_activos=False):
        return False

    excel = ctx.cursos.FJPP_crear("EXC-01", "Excel Intermedio", 40, "180.00")
    word = ctx.cursos.FJPP_crear("WRD-01", "Word Profesional", 30, "150.00")
    ctx.cursos.FJPP_crear("PPT-01", "PowerPoint Avanzado", 30, "150.00")

    ana = ctx.estudiantes.FJPP_crear("45678912", "Ana", "Quispe Mamani", "ana@example.com", "987654321")
    luis = ctx.estudiantes.FJPP_crear("71234567", "Luis", "Condori Huanca")
    rosa = ctx.estudiantes.FJPP_crear("40123456", "Rosa", "Apaza Flores")

    m_ana = ctx.matriculas.FJPP_matricular(ana, excel)
    ctx.pagos.FJPP_registrar(m_ana, "180.00", "TRANSFERENCIA", "OP-001")
    ctx.matriculas.FJPP_cambiar_estado(m_ana, "COMPLETADA")

    m_luis = ctx.matriculas.FJPP_matricular(luis, excel)
    ctx.pagos.FJPP_registrar(m_luis, "100.00", "EFECTIVO")

    m_rosa = ctx.matriculas.FJPP_matricular(rosa, word)
    ctx.pagos.FJPP_registrar(m_rosa, "150.00", "YAPE/PLIN", "YP-778")
    return True
