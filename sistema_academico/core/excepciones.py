"""Errores propios del sistema. La interfaz los muestra como mensajes simples."""


class FJPP_ErrorDeNegocio(Exception):
    """Una regla del negocio impide la operación (mensaje apto para el usuario)."""


class FJPP_ValidacionError(FJPP_ErrorDeNegocio):
    """Un dato ingresado no es válido."""


class FJPP_NoEncontrado(FJPP_ErrorDeNegocio):
    """No existe el registro buscado."""
