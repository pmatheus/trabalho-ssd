"""Modelos Pydantic refletindo contratos OpenAPI para Aluno (inicial)."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

def iso_now() -> str:
    """Retorna o horário UTC atual no formato ISO 8601 com 'Z'."""
    return datetime.utcnow().isoformat() + "Z"


class ResourceBase(BaseModel):
    id: str
    resourceType: str
    lastUpdated: str = Field(default_factory=iso_now)


class CursoShort(ResourceBase):
    codigo: Optional[str] = None
    nome: Optional[str] = None


class CurriculoShort(ResourceBase):
    codigo: Optional[str] = None


class PeriodoIngresso(BaseModel):
    ano: int
    periodo: int


class AlunoShort(ResourceBase):
    matricula: str
    nome: str


class Aluno(ResourceBase):
    matricula: str
    nome: str
    ira: Optional[float] = None
    periodoIngresso: PeriodoIngresso | None = None
    curso: Optional[CursoShort] = None
    curriculo: Optional[CurriculoShort] = None


class Link(BaseModel):
    self: str
    next: Optional[str] = None
    previous: Optional[str] = None


class SearchSetBase(BaseModel):
    resourceType: str
    total: int
    count: int
    offset: int
    link: Link


class AlunoSearchSet(SearchSetBase):
    items: List[AlunoShort]
