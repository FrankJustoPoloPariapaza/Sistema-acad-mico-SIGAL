"""Ensambla los módulos del sistema (inyección de dependencias sencilla)."""
from __future__ import annotations

from pathlib import Path

from core.database import FJPP_Database
from modulos.certificados import FJPP_ServicioCertificados
from modulos.cursos import FJPP_ServicioCursos
from modulos.estudiantes import FJPP_ServicioEstudiantes
from modulos.matriculas import FJPP_ServicioMatriculas
from modulos.pagos import FJPP_ServicioPagos
from modulos.reportes import FJPP_ServicioReportes


class FJPP_Contexto:
    def __init__(self, db: FJPP_Database, dir_certificados: Path | None = None,
                 dir_solicitudes: Path | None = None):
        self.db = db
        self.estudiantes = FJPP_ServicioEstudiantes(db)
        self.cursos = FJPP_ServicioCursos(db)
        self.matriculas = FJPP_ServicioMatriculas(db, self.estudiantes, self.cursos)
        self.pagos = FJPP_ServicioPagos(db, self.matriculas)
        self.certificados = FJPP_ServicioCertificados(
            db, self.matriculas, dir_certificados, dir_solicitudes
        )
        self.reportes = FJPP_ServicioReportes(db)
