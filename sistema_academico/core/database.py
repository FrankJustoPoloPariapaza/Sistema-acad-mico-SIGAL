"""Capa de acceso a datos (SQLite, solo biblioteca estándar)."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS estudiantes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    dni         TEXT NOT NULL UNIQUE,
    nombres     TEXT NOT NULL,
    apellidos   TEXT NOT NULL,
    email       TEXT NOT NULL DEFAULT '',
    telefono    TEXT NOT NULL DEFAULT '',
    activo      INTEGER NOT NULL DEFAULT 1,
    creado_en   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cursos (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo           TEXT NOT NULL UNIQUE,
    nombre           TEXT NOT NULL,
    horas            INTEGER NOT NULL CHECK (horas > 0),
    precio_centimos  INTEGER NOT NULL CHECK (precio_centimos >= 0),
    activo           INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS matriculas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    estudiante_id   INTEGER NOT NULL REFERENCES estudiantes(id),
    curso_id        INTEGER NOT NULL REFERENCES cursos(id),
    fecha           TEXT NOT NULL,
    -- Monto pactado al matricular (puede diferir del precio actual del curso)
    monto_centimos  INTEGER NOT NULL CHECK (monto_centimos >= 0),
    estado          TEXT NOT NULL DEFAULT 'EN_CURSO'
                    CHECK (estado IN ('EN_CURSO', 'COMPLETADA', 'RETIRADA')),
    UNIQUE (estudiante_id, curso_id)
);

CREATE TABLE IF NOT EXISTS pagos (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    matricula_id      INTEGER NOT NULL REFERENCES matriculas(id),
    nro_recibo        TEXT UNIQUE,
    monto_centimos    INTEGER NOT NULL CHECK (monto_centimos > 0),
    fecha             TEXT NOT NULL,
    metodo            TEXT NOT NULL,
    referencia        TEXT NOT NULL DEFAULT '',
    anulado           INTEGER NOT NULL DEFAULT 0,
    motivo_anulacion  TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS certificados (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    matricula_id       INTEGER NOT NULL UNIQUE REFERENCES matriculas(id),
    codigo             TEXT UNIQUE,
    estado             TEXT NOT NULL DEFAULT 'PENDIENTE_FIRMA'
                       CHECK (estado IN ('PENDIENTE_FIRMA', 'ENVIADO_A_FIRMA', 'FIRMADO')),
    fecha_solicitud    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_envio        TEXT,
    fecha_firmado      TEXT,
    archivo_pdf        TEXT,
    sha256             TEXT UNIQUE,
    firmas_detectadas  INTEGER NOT NULL DEFAULT 0,
    verificacion       TEXT NOT NULL DEFAULT 'NO_VERIFICADA'
);

CREATE INDEX IF NOT EXISTS idx_matriculas_estudiante ON matriculas(estudiante_id);
CREATE INDEX IF NOT EXISTS idx_pagos_matricula ON pagos(matricula_id);
"""


class FJPP_Database:
    def __init__(self, ruta: str | Path):
        self.ruta = str(ruta)
        if self.ruta != ":memory:":
            Path(self.ruta).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.ruta)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(SCHEMA)

    @contextmanager
    def FJPP_transaccion(self):
        """Confirma al salir sin errores; deshace todo si ocurre una excepción."""
        try:
            yield self._conn
            self._conn.commit()
        except BaseException:
            self._conn.rollback()
            raise

    def FJPP_consultar(self, sql: str, params=()) -> list[sqlite3.Row]:
        return self._conn.execute(sql, params).fetchall()

    def FJPP_consultar_uno(self, sql: str, params=()) -> sqlite3.Row | None:
        return self._conn.execute(sql, params).fetchone()

    def FJPP_cerrar(self) -> None:
        self._conn.close()
