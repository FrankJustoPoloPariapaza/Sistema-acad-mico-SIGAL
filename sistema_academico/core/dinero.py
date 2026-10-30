"""Manejo de dinero en céntimos (enteros) para evitar errores de redondeo."""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

import config
from core.excepciones import FJPP_ValidacionError


def FJPP_a_centimos(valor) -> int:
    """Convierte '150', '150.50' o '150,50' a céntimos (15000, 15050)."""
    texto = str(valor).strip().replace(",", ".")
    try:
        monto = Decimal(texto)
    except InvalidOperation:
        raise FJPP_ValidacionError("El monto no es un número válido.") from None
    if not monto.is_finite():
        raise FJPP_ValidacionError("El monto no es un número válido.")
    if monto < 0:
        raise FJPP_ValidacionError("El monto no puede ser negativo.")
    return int((monto * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def FJPP_formatear(centimos: int) -> str:
    return f"{config.MONEDA} {Decimal(centimos) / 100:,.2f}"
