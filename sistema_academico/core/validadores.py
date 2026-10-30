"""Validaciones de datos de entrada."""
from __future__ import annotations

import re
from datetime import date, datetime

from core.excepciones import FJPP_ValidacionError

_RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_RE_TELEFONO = re.compile(r"^\+?\d{6,15}$")


def FJPP_requerido(valor: str | None, campo: str) -> str:
    limpio = (valor or "").strip()
    if not limpio:
        raise FJPP_ValidacionError(f"{campo} es obligatorio.")
    return limpio


def FJPP_validar_dni(valor: str | None) -> str:
    dni = FJPP_requerido(valor, "El DNI")
    if not re.fullmatch(r"\d{8}", dni):
        raise FJPP_ValidacionError("El DNI debe tener exactamente 8 dígitos.")
    return dni


def FJPP_validar_email(valor: str | None) -> str:
    """El correo es opcional: devuelve '' si viene vacío."""
    email = (valor or "").strip().lower()
    if email and not _RE_EMAIL.match(email):
        raise FJPP_ValidacionError("El correo electrónico no es válido.")
    return email


def FJPP_validar_telefono(valor: str | None) -> str:
    """El teléfono es opcional: devuelve '' si viene vacío."""
    tel = (valor or "").replace(" ", "").replace("-", "")
    if tel and not _RE_TELEFONO.match(tel):
        raise FJPP_ValidacionError("El teléfono debe tener entre 6 y 15 dígitos.")
    return tel


def FJPP_entero_positivo(valor, campo: str) -> int:
    try:
        numero = int(str(valor).strip())
    except ValueError:
        raise FJPP_ValidacionError(f"{campo} debe ser un número entero.") from None
    if numero <= 0:
        raise FJPP_ValidacionError(f"{campo} debe ser mayor que cero.")
    return numero


def FJPP_validar_fecha(valor: str | None) -> str:
    """Acepta AAAA-MM-DD o DD/MM/AAAA y devuelve AAAA-MM-DD."""
    texto = FJPP_requerido(valor, "La fecha")
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, formato).date().isoformat()
        except ValueError:
            continue
    raise FJPP_ValidacionError("Fecha inválida. Use AAAA-MM-DD o DD/MM/AAAA.")


def FJPP_hoy_iso() -> str:
    return date.today().isoformat()
