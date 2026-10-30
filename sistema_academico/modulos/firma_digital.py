"""Inspección de PDF firmados digitalmente.

Los certificados los firman otras oficinas y llegan ya firmados. Este módulo NO
firma: solo (1) detecta si el PDF trae firma(s) incrustada(s) y (2) si está
instalada la biblioteca opcional ``pyHanko``, comprueba que el documento no fue
alterado desde que se firmó.

Importante: la detección sin pyHanko solo busca las estructuras de firma
(/ByteRange) dentro del archivo. Eso indica que el PDF *dice* estar firmado,
pero no prueba que la firma sea válida ni de confianza.
"""
from __future__ import annotations

import re
from pathlib import Path

NO_VERIFICADA = "NO_VERIFICADA"
VALIDA = "VALIDA"
INVALIDA = "INVALIDA"

_RE_BYTERANGE = re.compile(rb"/ByteRange\s*\[")


def FJPP_es_pdf(datos: bytes) -> bool:
    # La especificación permite algo de basura antes de la cabecera (primeros 1024 bytes).
    return b"%PDF-" in datos[:1024]


def FJPP_contar_firmas(datos: bytes) -> int:
    """Cantidad de diccionarios de firma (/ByteRange) encontrados en el PDF."""
    return len(_RE_BYTERANGE.findall(datos))


def FJPP_verificar(ruta: str | Path) -> tuple[str, str]:
    """Devuelve (estado, detalle). Estado: VALIDA, INVALIDA o NO_VERIFICADA."""
    try:
        from pyhanko.pdf_utils.reader import PdfFileReader
        from pyhanko.sign.validation import validate_pdf_signature
    except ImportError:
        return NO_VERIFICADA, (
            "pyHanko no está instalado: solo se detectó la presencia de firma, "
            "no se comprobó su integridad."
        )

    try:
        with open(ruta, "rb") as archivo:
            lector = PdfFileReader(archivo)
            firmas = list(lector.embedded_signatures)
            if not firmas:
                return NO_VERIFICADA, "No se encontraron firmas legibles."
            for firma in firmas:
                estado = validate_pdf_signature(firma)
                if not (estado.intact and estado.valid):
                    return INVALIDA, (
                        f"La firma '{firma.field_name}' no es íntegra: el documento "
                        "pudo ser alterado o la firma es inválida."
                    )
            return VALIDA, (
                f"{len(firmas)} firma(s) íntegra(s). La confianza en el certificado del "
                "firmante no se evalúa sin configurar una cadena de confianza."
            )
    except Exception as error:  # PDF corrupto o variante no soportada
        return NO_VERIFICADA, f"No se pudo verificar la firma: {error}"
