"""Genera artefactos verificables sin conexión a la base de datos."""
import json
import os
from dataclasses import asdict
from pathlib import Path

os.environ.setdefault("POSCOSEGRAN_BD_URL_APP", "postgresql+psycopg://export:export@localhost/export")
os.environ.setdefault("POSCOSEGRAN_JWT_EMISOR", "https://export.invalid/auth/v1")
os.environ.setdefault("POSCOSEGRAN_JWT_JWKS_URL", "https://export.invalid/jwks")

from poscosegran.api.app import crear_app
from poscosegran.dominio.campos import CAMPOS

raiz = Path(__file__).resolve().parents[2]
(raiz / "docs/openapi.json").write_text(json.dumps(crear_app().openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(raiz / "src/campos.json").write_text(json.dumps({k: asdict(v) for k, v in CAMPOS.items()}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
