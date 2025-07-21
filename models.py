"""Modelos Pydantic refletindo contratos OpenAPI para Aluno (inicial)."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class CursoShort(BaseModel):
    id: str
    resourceType: str
    codigo: Optional[str] = None
    nome: Optional[str] = None


class PeriodoIngresso(BaseModel):
    ano: int
    periodo: int
