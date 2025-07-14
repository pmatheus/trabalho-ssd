"""FastAPI application to expose SIGAA database data.

Prerequisites:
1. Run the PostgreSQL service via docker compose:

    cd trabalho2/postgres
    docker compose up -d

   This will expose Postgres on localhost:5432 with database/user/password already
   created by the SQL scripts located in `trabalho2/sql` (load them in the given
   order).

2. Install dependencies

    pip install fastapi uvicorn sqlalchemy psycopg2-binary python-dotenv

3. Run the API server

    uvicorn fastapi_app:app --reload

Environment variables (optional):
    DATABASE_URL : SQLAlchemy-compatible connection string.
                  Defaults to
                  postgresql+psycopg2://SIGAA:SIGAA@localhost:5432/SIGAA
"""
from __future__ import annotations

import os
from typing import List

from fastapi import FastAPI, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy import MetaData, create_engine, select, text

# SQL blocks fornecidos pelo professor
import queries
import models
from sqlalchemy.engine import Engine

from sqlalchemy.orm import Session, sessionmaker

# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------
DEFAULT_DATABASE_URL = "postgresql+psycopg2://SIGAA:SIGAA@localhost:5432/SIGAA"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None
_metadata: MetaData | None = None


def get_engine() -> Engine:
    """Return a singleton SQLAlchemy Engine instance."""
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    return _engine


def get_metadata() -> MetaData:
    global _metadata
    if _metadata is None:
        _metadata = MetaData()
        # Reflect tables from the existing database
        _metadata.reflect(bind=get_engine())
    return _metadata


def get_session() -> Session:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine())
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(title="SIGAA API", version="1.0.0")


# ---------------------------------------------------------------------------
# Aluno endpoints
# ---------------------------------------------------------------------------
@app.get("/Aluno", tags=["Aluno"], summary="Pesquisa alunos")
async def list_alunos(
    nome: str | None = Query(None, description="nome ou parte do nome do aluno"),
    unidade: str | None = Query(None, description="código da unidade"),
    curso: str | None = Query(None, description="código do curso"),
    periodoIngresso_ano: int | None = Query(None, ge=2000, le=2040, alias="periodoIngresso.ano", description="ano de ingresso"),
    periodoIngresso_periodo: int | None = Query(None, ge=1, le=2, alias="periodoIngresso.periodo", description="número do período letivo de ingresso do aluno"),
    size: int = Query(10, ge=1, le=100, description="tamanho da página (número de registros por página)"),
    offset: int = Query(0, ge=0, description="posicao do primerio registro da página (primeiro registro _offset=0)"),
    db: Session = Depends(get_session),
) -> dict:
    # Build periodoIngresso string from components if provided
    periodoIngresso = None
    if periodoIngresso_ano and periodoIngresso_periodo:
        periodoIngresso = f"{periodoIngresso_ano}.{periodoIngresso_periodo}"
    
    sql = text(queries.ALUNO_LIST)
    params = {
        "nome": nome,
        "curso": curso,
        "unidade": unidade,
        "periodoIngresso": periodoIngresso,
        "_pageOffset": offset,
        "_pageSize": size,
    }
    rows = db.execute(sql, params).mappings().all()
    total = rows[0]["_total"] if rows else 0
    
    items = []
    for row in rows:
        data = dict(row)
        data.pop("_total", None)
        items.append({
            "@type": "Aluno",
            "id": str(data.get("matricula", "")),
            "matricula": str(data.get("matricula", "")),
            "nome": data.get("nome", ""),
        })
    
    base_url = f"Aluno?size={size}&offset={offset}"
    links = {
        "self": base_url,
    }
    if (offset + size) < total:
        links["next"] = f"Aluno?size={size}&offset={offset + size}"
    if offset > 0:
        links["previous"] = f"Aluno?size={size}&offset={max(offset - size, 0)}"
    
    return {
        "total": total,
        "size": size,
        "offset": offset,
        "links": links,
        "values": items,
    }


@app.get("/Aluno/{id}", tags=["Aluno"], summary="Consultar um aluno")
async def read_aluno(
    id: str,
    db: Session = Depends(get_session),
) -> dict:
    row = db.execute(text(queries.ALUNO_DETAIL), {"id": id}).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Not found")
    
    data = dict(row)
    periodo = None
    if "periodo_ingresso_ano" in data and "periodo_ingresso_numero" in data:
        periodo = models.PeriodoIngresso(
            ano=int(data.pop("periodo_ingresso_ano")),
            periodo=int(data.pop("periodo_ingresso_numero")),
        )
    
    curso = None
    if data.get("curso_codigo"):
        curso = models.CursoShort(
            id=str(data.get("curso_codigo")),
            resourceType="Curso",
            codigo=str(data.get("curso_codigo")),
            nome=data.get("curso_nome"),
        )
    
    result = {
        "@type": "Aluno",
        "id": str(id),
        "matricula": data.get("matricula") or str(id),
        "nome": data.get("nome", ""),
    }
    
    if data.get("ira") is not None:
        result["ira"] = data.get("ira")
    
    if periodo:
        result["periodoIngresso"] = {
            "ano": periodo.ano,
            "periodo": periodo.periodo
        }
    
    if curso:
        result["curso"] = {
            "@type": "Curso",
            "id": curso.id,
            "codigo": curso.codigo,
            "nome": curso.nome,
        }
    
    # Add curriculo as a string reference if available
    if data.get("curriculo"):
        # Format as "Curriculo/{curso_id}.{curriculo_suffix}"
        curso_id = data.get("curso_codigo", "")
        curriculo_suffix = data.get("curriculo", "")
        if curso_id and curriculo_suffix:
            result["curriculo"] = f"Curriculo/{curso_id}.{curriculo_suffix}"
    
    return result


# ---------------------------------------------------------------------------
# Curso endpoints
# ---------------------------------------------------------------------------
class CursoSearchSet(BaseModel):
    resourceType: str = "Curso"
    total: int
    count: int
    offset: int
    link: models.Link
    items: List[dict]


@app.get("/Curso", tags=["Curso"], summary="Pesquisa cursos")
async def list_cursos(
    nome: str | None = Query(None, description="nome ou parte do nome do curso"),
    unidade: str | None = Query(None, description="código da unidade"),
    size: int = Query(10, ge=1, le=100, description="tamanho da página (número de registros por página)"),
    offset: int = Query(0, ge=0, description="posicao do primerio registro da página (primeiro registro _offset=0)"),
    db: Session = Depends(get_session),
) -> dict:
    sql = text(queries.CURSO_LIST)
    params = {
        "nome": nome,
        "unidade": unidade,
        "_pageOffset": offset,
        "_pageSize": size,
    }
    rows = db.execute(sql, params).mappings().all()
    total = rows[0]["_total"] if rows else 0
    
    items = []
    for row in rows:
        data = dict(row)
        data.pop("_total", None)
        # Column names are lowercase from the query
        curso_id = str(data.get("id", ""))
        item = {
            "@type": "Curso",
            "id": curso_id,
            "codigo": curso_id,  # For Curso, codigo and id are the same
            "nome": data.get("nome", ""),
        }
        items.append(item)
    
    base_url = f"Curso?size={size}&offset={offset}"
    links = {
        "self": base_url,
    }
    if (offset + size) < total:
        links["next"] = f"Curso?size={size}&offset={offset + size}"
    if offset > 0:
        links["previous"] = f"Curso?size={size}&offset={max(offset - size, 0)}"
    
    return {
        "total": total,
        "size": size,
        "offset": offset,
        "links": links,
        "values": items,
    }


@app.get("/Curso/{id}", tags=["Curso"], summary="Consultar um curso")
async def read_curso(
    id: str,
    db: Session = Depends(get_session),
) -> dict:
    row = db.execute(text(queries.CURSO_DETAIL), {"id": id}).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Not found")
    
    data = dict(row)
    
    result = {
        "@type": "Curso",
        "id": str(id),
        "codigo": str(id),
        "nome": data.get("nome", ""),
    }
    
    # Add optional fields if present
    if data.get("grau_academico"):
        result["grauAcademico"] = data.get("grau_academico")
    
    if data.get("modalidade"):
        # Map modalidade values
        modalidade = data.get("modalidade")
        if modalidade == "P":
            result["modalidade"] = "Presencial"
        elif modalidade == "D":
            result["modalidade"] = "Ead"
        else:
            result["modalidade"] = modalidade
    
    if data.get("turno"):
        # Map turno values
        turno = data.get("turno")
        if turno == "D":
            result["turno"] = "Diurno"
        elif turno == "N":
            result["turno"] = "Noturno"
        else:
            result["turno"] = turno
    
    # Fetch unidades for this curso
    unidades_rows = db.execute(text(queries.CURSO_UNIDADES), {"curso_id": id}).mappings().all()
    result["unidade"] = []
    for unidade_row in unidades_rows:
        result["unidade"].append({
            "codigo": unidade_row.get("codigo", ""),
            "nome": unidade_row.get("nome", "")
        })
    
    # Add coordenador if available
    if data.get("coordenador"):
        result["coordenador"] = {
            "nome": data.get("coordenador")
        }
    
    return result


# ---------------------------------------------------------------------------
# Disciplina endpoints
# ---------------------------------------------------------------------------
class DisciplinaSearchSet(BaseModel):
    resourceType: str = "Disciplina"
    total: int
    count: int
    offset: int
    link: models.Link
    items: List[dict]


# @app.get("/Disciplina", tags=["Disciplina"], summary="Pesquisa disciplinas")
# async def list_disciplinas(
#     nome: str | None = Query(None, description="Nome ou parte do nome da disciplina"),
#     codigo: str | None = Query(None, description="Código ou parte do código da disciplina"),
#     unidade: str | None = Query(None, description="Código da unidade organizacional"),
#     modalidade: str | None = Query(None, description="Modalidade da disciplina"),
#     cargaHorariaMin: int | None = Query(None, ge=0, description="Carga horária mínima total"),
#     cargaHorariaMax: int | None = Query(None, ge=0, description="Carga horária máxima total"),
#     _count: int = Query(10, ge=1, le=100, description="Número de registro retornados por página"),
#     _offset: int = Query(0, ge=0, description="Índice do primeiro registro da página atual"),
#     db: Session = Depends(get_session),
# ) -> DisciplinaSearchSet:
#     sql = text(queries.DISCIPLINA_LIST)
#     params = {
#         "nome": nome,
#         "modalidade": modalidade,
#         "unidade": unidade,
#         "_pageOffset": _offset,
#         "_pageSize": _count,
#     }
#     rows = db.execute(sql, params).mappings().all()
#     total = rows[0]["_total"] if rows else 0
    
#     items = []
#     for row in rows:
#         data = dict(row)
#         data.pop("_total", None)
#         disciplina_id = str(data.get("id", ""))
#         item = {
#             "id": disciplina_id,
#             "resourceType": "Disciplina",
#             "codigo": disciplina_id,  # For Disciplina, codigo and id are the same
#             "nome": data.get("nome", ""),
#             "lastUpdated": models.iso_now(),
#         }
#         if "carga_horaria_total" in data:
#             item["cargaHorariaTotal"] = data["carga_horaria_total"]
#         items.append(item)
    
#     base_url = f"Disciplina?_count={_count}&_offset={_offset}"
#     link = models.Link(
#         self=base_url,
#         next=f"Disciplina?_count={_count}&_offset={_offset + _count}" if (_offset + _count) < total else None,
#         previous=f"Disciplina?_count={_count}&_offset={max(_offset - _count, 0)}" if _offset > 0 else None,
#     )
    
#     return DisciplinaSearchSet(
#         resourceType="Disciplina",
#         total=total,
#         count=_count,
#         offset=_offset,
#         link=link,
#         items=items,
#     )


# @app.get("/Disciplina/{id}", tags=["Disciplina"], summary="Consultar uma disciplina")
# async def read_disciplina(
#     id: str,
#     db: Session = Depends(get_session),
# ) -> dict:
#     # Use generic query for now as we don't have DISCIPLINA_DETAIL
#     metadata = get_metadata()
#     table = metadata.tables.get("sigaa_disciplina")
#     if table is None:
#         raise HTTPException(status_code=500, detail="Tabela 'sigaa_disciplina' não encontrada no banco")
    
#     id_column = list(table.primary_key.columns)[0]
#     row = db.execute(select(table).where(id_column == id)).mappings().first()
#     if row is None:
#         raise HTTPException(status_code=404, detail="Not found")
    
#     data = dict(row)
#     data["id"] = str(id)
#     data["resourceType"] = "Disciplina"
#     return data


# ---------------------------------------------------------------------------
# Curriculo endpoints
# ---------------------------------------------------------------------------
@app.get("/Curriculo", tags=["Curriculo"], summary="Pesquisa currículos")
async def list_curriculos(
    curso: str = Query(..., description="código do curso desejado"),
    status: str | None = Query(None, description="status"),
    size: int = Query(10, ge=1, le=100, description="tamanho da página (número de registros por página)"),
    offset: int = Query(0, ge=0, description="posicao do primerio registro da página (primeiro registro offset=0)"),
    db: Session = Depends(get_session),
) -> dict:
    sql = text(queries.CURRICULO_LIST)
    params = {
        "curso": curso,
        "_pageOffset": offset,
        "_pageSize": size,
    }
    rows = db.execute(sql, params).mappings().all()
    
    items = []
    for row in rows:
        data = dict(row)
        data.pop("_total", None)
        # The query returns just the numeric part (e.g., "2" instead of "6351.2")
        curriculo_suffix = str(data.get("id", ""))
        # Construct the full curriculo ID as "curso.suffix"
        curriculo_id = f"{curso}.{curriculo_suffix}" if curso and curriculo_suffix else curriculo_suffix
        
        item = {
            "@type": "Curriculo",
            "id": curriculo_id,
            "codigo": curriculo_id,
            "status": data.get("status", "").lower() if data.get("status") else "",
        }
        # Add curso info from the query result
        if data.get("curso_codigo"):
            item["curso"] = {
                "@type": "Curso",
                "id": str(data.get("curso_codigo", "")),
                "codigo": str(data.get("curso_codigo", "")),
                "nome": data.get("curso_nome", ""),
            }
        # Add inicioVigencia if available
        if data.get("periodo_letivo_vigor_ano") and data.get("periodo_letivo_vigor_numero"):
            item["inicioVigencia"] = {
                "ano": int(data.get("periodo_letivo_vigor_ano")),
                "periodo": int(data.get("periodo_letivo_vigor_numero")),
            }
        # Add fimVigencia as null (not available in current query)
        item["fimVigencia"] = None
        items.append(item)
    
    # Filter by status if provided
    if status:
        items = [item for item in items if item.get("status") == status]
    
    # Get total count after filtering
    filtered_total = len(items)
    
    # Apply pagination to filtered items
    paginated_items = items[offset:offset + size]
    
    base_url = f"Curriculo?curso={curso}&size={size}&offset={offset}"
    if status:
        base_url += f"&status={status}"
    
    links = {
        "self": base_url,
    }
    if (offset + size) < filtered_total:
        links["next"] = f"Curriculo?curso={curso}&size={size}&offset={offset + size}" + (f"&status={status}" if status else "")
    if offset > 0:
        links["previous"] = f"Curriculo?curso={curso}&size={size}&offset={max(offset - size, 0)}" + (f"&status={status}" if status else "")
    
    return {
        "total": filtered_total,
        "size": size,
        "offset": offset,
        "links": links,
        "values": paginated_items,
    }


@app.get("/Curriculo/{id}", tags=["Curriculo"], summary="Consultar um currículo")
async def read_curriculo(
    id: str,
    db: Session = Depends(get_session),
) -> dict:
    # The ID can come as "6351.2" from the API but needs to be "6351/2" for the database
    # The CURRICULO_DETAIL query expects the ID without the slash or dot
    row = db.execute(text(queries.CURRICULO_DETAIL), {"id": id}).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Not found")
    
    data = dict(row)
    
    # Build the response according to the OpenAPI spec
    result = {
        "@type": "Curriculo",
        "id": data.get("id", id),  # This should already be in "6351.2" format from the query
        "codigo": data.get("id", id),
        "status": data.get("status", "").lower() if data.get("status") else "",
    }
    
    # Add cargaHoraria object if any values present
    carga_horaria = {}
    if data.get("carga_horaria_minima_total") is not None:
        carga_horaria["totalMinima"] = int(data.get("carga_horaria_minima_total"))
    if data.get("carga_horaria_obr") is not None:
        carga_horaria["obrigatoria"] = int(data.get("carga_horaria_obr"))
    if data.get("carga_horaria_minima_opt") is not None:
        carga_horaria["optativaMinima"] = int(data.get("carga_horaria_minima_opt"))
    if data.get("carga_horaria_eletiva_max") is not None:
        carga_horaria["componentesEletivosMaxima"] = int(data.get("carga_horaria_eletiva_max"))
    if data.get("carga_horaria_max_periodo") is not None:
        carga_horaria["periodoLetivoMaxima"] = int(data.get("carga_horaria_max_periodo"))
    
    if carga_horaria:
        result["cargaHoraria"] = carga_horaria
    
    # Add prazoConclusao object if any values present
    prazo_conclusao = {}
    if data.get("min_periodos") is not None:
        prazo_conclusao["minimo"] = int(data.get("min_periodos"))
    if data.get("num_periodos") is not None:
        prazo_conclusao["medio"] = int(data.get("num_periodos"))
    if data.get("max_periodos") is not None:
        prazo_conclusao["maximo"] = int(data.get("max_periodos"))
    
    if prazo_conclusao:
        result["prazoConclusao"] = prazo_conclusao
    
    # Add curso info if available
    if data.get("curso_id"):
        result["curso"] = {
            "@type": "Curso",
            "id": str(data.get("curso_id")),
            "codigo": str(data.get("curso_id")),
            "nome": data.get("curso_nome", ""),
        }
    
    # Add inicioVigencia if available
    if data.get("periodo_letivo_vigor_ano") and data.get("periodo_letivo_vigor_numero"):
        result["inicioVigencia"] = {
            "ano": int(data.get("periodo_letivo_vigor_ano")),
            "periodo": int(data.get("periodo_letivo_vigor_numero")),
        }
    
    # Add fimVigencia as null (not available in current query)
    result["fimVigencia"] = None
    
    return result


@app.get("/Curriculo/{id}/disciplina", tags=["Curriculo"], summary="Pesquisar disciplinas de uma estrutura curricular")
async def list_curriculo_disciplinas(
    id: str,
    nivel: int | None = Query(None, ge=1, le=14, description="Nível da disciplina no currículo"),
    tipo: str | None = Query(None, description="Tipo de vínculo da disciplina (obrigatoria, optativa)"),
    unidade: str | None = Query(None, description="Código da unidade organizacional"),
    db: Session = Depends(get_session),
) -> List[dict]:
    # Convert tipo to database format if provided
    tipo_db = None
    if tipo:
        if tipo == "obrigatoria":
            tipo_db = "OBR"
        elif tipo == "optativa":
            tipo_db = "OPT"
    
    sql = text(queries.CURRICULO_DISCIPLINA_LIST)
    params = {
        "id": id,
        "nivel": nivel,
        "tipo": tipo_db,
        "unidade": unidade,
    }
    rows = db.execute(sql, params).mappings().all()
    
    items = []
    for row in rows:
        data = dict(row)
        disciplina_id = str(data.get("id", ""))
        
        item = {
            "@type": "Disciplina",
            "id": disciplina_id,
            "codigo": disciplina_id,
            "nome": data.get("nome", ""),
            "nivel": data.get("nivel"),
            "tipo": data.get("tipo", ""),
        }
        
        # Add unidade info if available
        if data.get("unidade_codigo"):
            item["unidade"] = {
                "codigo": str(data.get("unidade_codigo", "")),
                "nome": data.get("unidade_nome", ""),
            }
        
        items.append(item)
    
    return items


@app.get("/Curriculo/{id}/disciplina/{disciplina}", tags=["Curriculo"], summary="Consultar uma disciplina de uma estrutura curricular")
async def read_curriculo_disciplina(
    id: str,
    disciplina: str,
    db: Session = Depends(get_session),
) -> dict:
    sql = text(queries.CURRICULO_DISCIPLINA_DETAIL)
    params = {
        "id": id,
        "disciplina": disciplina,
    }
    row = db.execute(sql, params).mappings().first()
    
    if row is None:
        raise HTTPException(status_code=404, detail="Not found")
    
    data = dict(row)
    disciplina_id = str(data.get("id", disciplina))
    
    result = {
        "@type": "Disciplina",
        "id": disciplina_id,
        "codigo": disciplina_id,
        "nome": data.get("nome", ""),
        "nivel": data.get("nivel"),
        "tipo": data.get("tipo", ""),
    }
    
    # Add carga horaria presencial if available
    if any(data.get(field) is not None for field in ["carga_horaria_teorica", "carga_horaria_pratica", "carga_horaria_extensionista"]):
        result["cargaHorariaPresencial"] = {}
        if data.get("carga_horaria_teorica") is not None:
            result["cargaHorariaPresencial"]["teorica"] = int(data.get("carga_horaria_teorica"))
        if data.get("carga_horaria_pratica") is not None:
            result["cargaHorariaPresencial"]["pratica"] = int(data.get("carga_horaria_pratica"))
        if data.get("carga_horaria_extensionista") is not None:
            result["cargaHorariaPresencial"]["extensionista"] = int(data.get("carga_horaria_extensionista"))
    
    # Add unidade info if available
    if data.get("unidade_codigo"):
        result["unidade"] = {
            "codigo": str(data.get("unidade_codigo", "")),
            "nome": data.get("unidade_nome", ""),
        }
    
    return result