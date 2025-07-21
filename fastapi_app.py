"""Aplicação FastAPI para expor dados do banco SIGAA.

Pré-requisitos:
1. Execute o serviço PostgreSQL via docker compose:

    cd trabalho2/postgres
    docker compose up -d

   Isso irá expor o Postgres em localhost:5432 com banco/usuário/senha já
   criados pelos scripts SQL localizados em `trabalho2/sql` (carregue-os na
   ordem fornecida).

2. Instale as dependências

    pip install fastapi uvicorn sqlalchemy psycopg2-binary python-dotenv

3. Execute o servidor da API

    uvicorn fastapi_app:app --reload

Variáveis de ambiente (opcionais):
    DATABASE_URL : String de conexão compatível com SQLAlchemy.
                  Padrão:
                  postgresql+psycopg2://SIGAA:SIGAA@localhost:5432/SIGAA
"""
from __future__ import annotations

import os
from typing import List

from fastapi import FastAPI, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy import MetaData, create_engine, select, text

# Blocos SQL fornecidos pelo professor
import queries
import models
from sqlalchemy.engine import Engine

from sqlalchemy.orm import Session, sessionmaker

# ---------------------------------------------------------------------------
# Configuração do banco de dados
# ---------------------------------------------------------------------------
DEFAULT_DATABASE_URL = "postgresql+psycopg2://SIGAA:SIGAA@localhost:5432/SIGAA"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None
_metadata: MetaData | None = None


def get_engine() -> Engine:
    """Retorna uma instância singleton do SQLAlchemy Engine."""
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    return _engine


def get_metadata() -> MetaData:
    global _metadata
    if _metadata is None:
        _metadata = MetaData()
        # Reflete tabelas do banco de dados existente
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
# Aplicação FastAPI
# ---------------------------------------------------------------------------
app = FastAPI(title="SIGAA API", version="1.0.0")


# ---------------------------------------------------------------------------
# Endpoints de Aluno
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
    # Constrói string periodoIngresso a partir dos componentes se fornecidos
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
    
    # Adiciona currículo como referência string se disponível
    if data.get("curriculo"):
        # Formata como "Curriculo/{curso_id}.{curriculo_suffix}"
        curso_id = data.get("curso_codigo", "")
        curriculo_suffix = data.get("curriculo", "")
        if curso_id and curriculo_suffix:
            result["curriculo"] = f"Curriculo/{curso_id}.{curriculo_suffix}"
    
    return result


# ---------------------------------------------------------------------------
# Endpoints de Curso
# ---------------------------------------------------------------------------

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
        # Nomes das colunas estão em minúsculas da consulta
        curso_id = str(data.get("id", ""))
        item = {
            "@type": "Curso",
            "id": curso_id,
            "codigo": curso_id,  # Para Curso, código e identificador são iguais
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
    
    # Adiciona campos opcionais se presentes
    if data.get("grau_academico"):
        result["grauAcademico"] = data.get("grau_academico")
    
    if data.get("modalidade"):
        # Mapeia valores de modalidade
        modalidade = data.get("modalidade")
        if modalidade == "P":
            result["modalidade"] = "Presencial"
        elif modalidade == "D":
            result["modalidade"] = "Ead"
        else:
            result["modalidade"] = modalidade
    
    if data.get("turno"):
        # Mapeia valores de turno
        turno = data.get("turno")
        if turno == "D":
            result["turno"] = "Diurno"
        elif turno == "N":
            result["turno"] = "Noturno"
        else:
            result["turno"] = turno
    
    # Busca unidades para este curso
    unidades_rows = db.execute(text(queries.CURSO_UNIDADES), {"curso_id": id}).mappings().all()
    result["unidade"] = []
    for unidade_row in unidades_rows:
        result["unidade"].append({
            "codigo": unidade_row.get("codigo", ""),
            "nome": unidade_row.get("nome", "")
        })
    
    # Adiciona coordenador se disponível
    if data.get("coordenador"):
        result["coordenador"] = {
            "nome": data.get("coordenador")
        }
    
    return result


# ---------------------------------------------------------------------------
# Endpoints de Currículo
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
        # A consulta retorna apenas a parte numérica (ex: "2" ao invés de "6351.2")
        curriculo_suffix = str(data.get("id", ""))
        # Constrói o ID completo do currículo como "curso.sufixo"
        curriculo_id = f"{curso}.{curriculo_suffix}" if curso and curriculo_suffix else curriculo_suffix
        
        item = {
            "@type": "Curriculo",
            "id": curriculo_id,
            "codigo": curriculo_id,
            "status": data.get("status", "").lower() if data.get("status") else "",
        }
        # Adiciona informações do curso do resultado da consulta
        if data.get("curso_codigo"):
            item["curso"] = {
                "@type": "Curso",
                "id": str(data.get("curso_codigo", "")),
                "codigo": str(data.get("curso_codigo", "")),
                "nome": data.get("curso_nome", ""),
            }
        # Adiciona inicioVigencia se disponível
        if data.get("periodo_letivo_vigor_ano") and data.get("periodo_letivo_vigor_numero"):
            item["inicioVigencia"] = {
                "ano": int(data.get("periodo_letivo_vigor_ano")),
                "periodo": int(data.get("periodo_letivo_vigor_numero")),
            }
        # Adiciona fimVigencia como null (não disponível na consulta atual)
        item["fimVigencia"] = None
        items.append(item)
    
    # Filtra por status se fornecido
    if status:
        items = [item for item in items if item.get("status") == status]
    
    # Obtém contagem total após filtragem
    filtered_total = len(items)
    
    # Aplica paginação aos itens filtrados
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
    # O ID pode vir como "6351.2" da API mas precisa ser "6351/2" para o banco de dados
    # A consulta CURRICULO_DETAIL espera o ID sem a barra ou ponto
    row = db.execute(text(queries.CURRICULO_DETAIL), {"id": id}).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Not found")
    
    data = dict(row)
    
    # Constrói a resposta de acordo com a especificação OpenAPI
    result = {
        "@type": "Curriculo",
        "id": data.get("id", id),  # Isso já deve estar no formato "6351.2" da consulta
        "codigo": data.get("id", id),
        "status": data.get("status", "").lower() if data.get("status") else "",
    }
    
    # Adiciona objeto cargaHoraria se algum valor estiver presente
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
    
    # Adiciona objeto prazoConclusao se algum valor estiver presente
    prazo_conclusao = {}
    if data.get("min_periodos") is not None:
        prazo_conclusao["minimo"] = int(data.get("min_periodos"))
    if data.get("num_periodos") is not None:
        prazo_conclusao["medio"] = int(data.get("num_periodos"))
    if data.get("max_periodos") is not None:
        prazo_conclusao["maximo"] = int(data.get("max_periodos"))
    
    if prazo_conclusao:
        result["prazoConclusao"] = prazo_conclusao
    
    # Adiciona informações do curso se disponível
    if data.get("curso_id"):
        result["curso"] = {
            "@type": "Curso",
            "id": str(data.get("curso_id")),
            "codigo": str(data.get("curso_id")),
            "nome": data.get("curso_nome", ""),
        }
    
    # Adiciona inicioVigencia se disponível
    if data.get("periodo_letivo_vigor_ano") and data.get("periodo_letivo_vigor_numero"):
        result["inicioVigencia"] = {
            "ano": int(data.get("periodo_letivo_vigor_ano")),
            "periodo": int(data.get("periodo_letivo_vigor_numero")),
        }
    
    # Adiciona fimVigencia como null (não disponível na consulta atual)
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
    # Converte tipo para formato do banco de dados se fornecido
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
        
        # Adiciona informações da unidade se disponível
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
    
    # Adiciona carga horária presencial se disponível
    if any(data.get(field) is not None for field in ["carga_horaria_teorica", "carga_horaria_pratica", "carga_horaria_extensionista"]):
        result["cargaHorariaPresencial"] = {}
        if data.get("carga_horaria_teorica") is not None:
            result["cargaHorariaPresencial"]["teorica"] = int(data.get("carga_horaria_teorica"))
        if data.get("carga_horaria_pratica") is not None:
            result["cargaHorariaPresencial"]["pratica"] = int(data.get("carga_horaria_pratica"))
        if data.get("carga_horaria_extensionista") is not None:
            result["cargaHorariaPresencial"]["extensionista"] = int(data.get("carga_horaria_extensionista"))
    
    # Adiciona informações da unidade se disponível
    if data.get("unidade_codigo"):
        result["unidade"] = {
            "codigo": str(data.get("unidade_codigo", "")),
            "nome": data.get("unidade_nome", ""),
        }
    
    return result