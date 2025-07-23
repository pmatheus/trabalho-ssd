"""SQL fornecido pelo professor para endpoints da API.
Apenas consultas de Aluno por enquanto; estenda com outras conforme necessário.
"""

ALUNO_DETAIL = (
    """
select
    alu.MATRICULA,
    alu.NOME,
    ac.CURSO as CURSO_CODIGO,
    cur.NOME as CURSO_NOME,
    ac.CURRICULO,
    ac.IRA,
    substring(ac.PERIODO_LETIVO_REGISTRO from 1 for 4) as PERIODO_INGRESSO_ANO,
    substring(ac.PERIODO_LETIVO_REGISTRO from 5) as PERIODO_INGRESSO_NUMERO
from SIGAA_ALUNO alu
inner join SIGAA_RL_ALUNO_CURSO ac ON alu.MATRICULA = ac.ALUNO
left join SIGAA_CURSO cur on ac.CURSO = cur.ID
where alu.MATRICULA = :id
    """
)

# A consulta de lista inclui uma coluna de contagem de janela _total para paginação
ALUNO_LIST = (
    """
select
    count(alu.MATRICULA) over() as _total,
    alu.MATRICULA,
    alu.NOME
from SIGAA_ALUNO alu
inner join SIGAA_RL_ALUNO_CURSO ac ON alu.MATRICULA = ac.ALUNO
left join SIGAA_RL_CURSO_UNIDADE cu ON ac.CURSO = cu.CURSO
where (unaccent(alu.NOME) ilike '%'||unaccent(:nome)||'%' or :nome is null)
  and (ac.CURSO = :curso or :curso is null)
  and (cu.UNIDADE = :unidade or :unidade is null)
  and ((ac.PERIODO_LETIVO_REGISTRO = substring(:periodoIngresso from 1 for 4)||substring(:periodoIngresso from 6))
       or :periodoIngresso is null)
order by alu.MATRICULA, alu.NOME
offset :_pageOffset
limit :_pageSize
    """
)

# ---------------- Curso ----------------
CURSO_DETAIL = """
select  
  cur.ID,
  cur.NOME,
  cur.GRAU_ACADEMICO,
  cur.TURNO,
  cur.MODALIDADE,
  cur.COORDENADOR
from SIGAA_CURSO cur
where cur.ID = :id
"""

CURSO_UNIDADES = """
select
  u.ID as CODIGO,
  u.NOME
from SIGAA_RL_CURSO_UNIDADE cu
inner join SIGAA_UNIDADE u on cu.UNIDADE = u.ID
where cu.CURSO = :curso_id
order by u.NOME
"""

CURSO_LIST = """
select  
  count(cur.ID) over() as _total,
  cur.ID,
  cur.NOME
from SIGAA_CURSO cur
inner join SIGAA_RL_CURSO_UNIDADE rcu on cur.ID = rcu.CURSO 
where (unaccent(cur.NOME) ilike '%'||unaccent(:nome)||'%' or :nome is null) and
      (rcu.UNIDADE = :unidade or :unidade is null)
order by cur.ID, cur.NOME 
offset :_pageOffset 
limit :_pageSize
"""

# ---------------- Disciplina ----------------
DISCIPLINA_DETAIL = """
select  
  dis.ID,
  dis.NOME,
  dis.MODALIDADE, 
  dis.CARGA_HORARIA_TEORICA,
  dis.CARGA_HORARIA_PRATICA,
  dis.CARGA_HORARIA_TEORICA+dis.CARGA_HORARIA_PRATICA as CARGA_HORARIA_TOTAL,
  und.ID as UNIDADE_CODIGO,
  und.NOME as UNIDADE_NOME
from SIGAA_DISCIPLINA dis
left join SIGAA_UNIDADE und ON dis.UNIDADE = und.ID 
where dis.ID = :id
"""

DISCIPLINA_LIST = """
select
  count(dis.ID) over() as _total,
  dis.ID,
  dis.NOME,
  und.ID as UNIDADE_CODIGO,
  und.NOME as UNIDADE_NOME
from SIGAA_DISCIPLINA dis
left join SIGAA_UNIDADE und ON dis.UNIDADE = und.ID 
where (unaccent(dis.NOME) ilike '%'||unaccent(:nome)||'%' or :nome is null) and
      (dis.modalidade = :modalidade or :modalidade is null) and
      (dis.UNIDADE = :unidade or :unidade is null)
order by dis.ID, dis.NOME 
offset :_pageOffset 
limit :_pageSize
"""

# ---------------- Currículo ----------------
CURRICULO_LIST = """
select 
    count(ec.ID) over() as _total,
    substring(ec.ID from 6) as ID, 
    case
        when ec.STATUS = 'A' then 'ativo'
        when ec.STATUS = 'I' then 'inativo'
    end as STATUS,
    substring(ec.PERIODO_LETIVO_VIGOR from 1 for 4) as PERIODO_LETIVO_VIGOR_ANO,
    substring(ec.PERIODO_LETIVO_VIGOR from 5) as PERIODO_LETIVO_VIGOR_NUMERO,
    sc.ID as CURSO_CODIGO,
    sc.NOME as CURSO_NOME
FROM public.SIGAA_CURRICULO ec
inner join SIGAA_RL_CURRICULO_CURSO srcc ON ec.ID = srcc.CURRICULO 
inner join SIGAA_CURSO sc ON srcc.CURSO = sc.ID
where srcc.CURSO = :curso
    and (case when ec.STATUS = 'A' then 'ativo' when ec.STATUS = 'I' then 'inativo' end = :status or :status is null)
order by substring(ec.ID from 6)
offset :_pageOffset 
limit :_pageSize
"""

CURRICULO_DETAIL = """
select 
    substring(ec.ID from 1 for 4) || '.' || substring(ec.ID from 6) as ID, 
    case
        when ec.STATUS = 'A' then 'ativo'
        when ec.STATUS = 'I' then 'inativo'
    end as STATUS,
    substring(ec.PERIODO_LETIVO_VIGOR from 1 for 4) as PERIODO_LETIVO_VIGOR_ANO,
    substring(ec.PERIODO_LETIVO_VIGOR from 5) as PERIODO_LETIVO_VIGOR_NUMERO,
    ec.CARGA_HORARIA_MINIMA_TOTAL, 
    ec.CARGA_HORARIA_MINIMA_OPT, 
    ec.CARGA_HORARIA_OBR, 
    ec.CARGA_HORARIA_ELETIVA_MAX, 
    ec.CARGA_HORARIA_MAX_PERIODO, 
    ec.NUM_PERIODOS, 
    ec.MIN_PERIODOS, 
    ec.MAX_PERIODOS,
    sc.id as CURSO_ID,
    sc.nome as CURSO_NOME
FROM public.SIGAA_CURRICULO ec
left join public.sigaa_rl_curriculo_curso srcc on srcc.curriculo = ec.ID
left join public.sigaa_curso sc on srcc.curso = sc.id 
where ec.ID = substring(:id from 1 for 4)||'/'||substring(:id from 6)
"""

CURRICULO_DISCIPLINA_LIST = """
select 
    cd.DISCIPLINA as ID,
    d.NOME,
    cd.PERIODO as NIVEL,
    case
        when cd.TIPO = 'OBR' then 'obrigatoria'
        when cd.TIPO = 'OPT' then 'optativa'
    end as TIPO,
    u.ID as UNIDADE_CODIGO,
    u.NOME as UNIDADE_NOME
from SIGAA_RL_CURRICULO_DISCIPLINA cd
inner join SIGAA_DISCIPLINA d on cd.DISCIPLINA = d.ID
left join SIGAA_UNIDADE u on d.UNIDADE = u.ID
where cd.CURRICULO = substring(:id from 1 for 4)||'/'||substring(:id from 6)
    and (cd.PERIODO = :nivel or :nivel is null)
    and (cd.TIPO = :tipo or :tipo is null)
    and (d.UNIDADE = :unidade or :unidade is null)
order by cd.PERIODO, cd.TIPO, d.NOME
"""

CURRICULO_DISCIPLINA_DETAIL = """
select 
    cd.DISCIPLINA as ID,
    d.NOME,
    cd.PERIODO as NIVEL,
    case
        when cd.TIPO = 'OBR' then 'obrigatoria'
        when cd.TIPO = 'OPT' then 'optativa'
    end as TIPO,
    d.CARGA_HORARIA_TEORICA,
    d.CARGA_HORARIA_PRATICA,
    0 as CARGA_HORARIA_EXTENSIONISTA,
    u.ID as UNIDADE_CODIGO,
    u.NOME as UNIDADE_NOME
from SIGAA_RL_CURRICULO_DISCIPLINA cd
inner join SIGAA_DISCIPLINA d on cd.DISCIPLINA = d.ID
left join SIGAA_UNIDADE u on d.UNIDADE = u.ID
where cd.CURRICULO = substring(:id from 1 for 4)||'/'||substring(:id from 6)
    and cd.DISCIPLINA = :disciplina
"""
