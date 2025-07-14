# Trabalho de Segurança em Sistemas Distribuídos(SSD)

API REST para acesso aos dados do sistema SIGAA, implementada com FastAPI e PostgreSQL conforme especificações openapi disponibilizadas pelo professor.

## 🐳 Instalação do Docker

### macOS
1. Baixe e instale o Docker Desktop: https://www.docker.com/products/docker-desktop/
2. Abra o Docker Desktop e aguarde inicializar
3. Verifique a instalação:
   ```bash
   docker --version
   ```

### Windows
1. Baixe e instale o Docker Desktop: https://www.docker.com/products/docker-desktop/
2. Certifique-se de que o WSL 2 está instalado
3. Abra o Docker Desktop
4. Verifique a instalação:
   ```powershell
   docker --version
   ```

## 🚀 Como Executar

1. **Clone o repositório e entre na pasta do projeto:**
   ```bash
   git clone https://github.com/seu-usuario/trabalho-ssd.git
   cd trabalho-ssd
   ```

2. **Inicie os serviços:**
   ```bash
   docker compose up -d
   ```
   
   Aguarde cerca de 30 segundos na primeira execução para o banco ser criado e populado.

3. **Acesse a API:**
   - Documentação interativa: http://localhost:8000/docs
   - API base: http://localhost:8000

## 🐛 Solução de Problemas

### Porta em uso
Se as portas 5432 ou 8000 já estiverem em uso, pare os processos ou edite as portas no `docker-compose.yml`.

### Reset completo
```bash
docker compose down -v
docker compose up -d
```

## 📊 Endpoints Disponíveis

### 👥 Alunos
- `GET /Aluno` - Lista alunos com paginação
  - Query params:
    - `nome`: Nome do aluno (busca parcial)
    - `curso`: Código do curso
    - `unidade`: Código da unidade
    - `periodoIngresso`: Período de ingresso (formato: "YYYY/S" ex: "2023/1")
    - `_count`: Quantidade de registros por página (padrão: 10)
    - `_offset`: Número de registros a pular
- `GET /Aluno/{matricula}` - Busca aluno específico por matrícula

### 📚 Cursos  
- `GET /Curso` - Lista cursos com paginação
  - Query params:
    - `nome`: Nome do curso (busca parcial)
    - `grau`: Grau do curso
    - `turno`: Turno (DIURNO, NOTURNO, MISTO)
    - `modalidade`: Modalidade (PRESENCIAL, EAD)
    - `_count`: Quantidade de registros por página (padrão: 10)
    - `_offset`: Número de registros a pular
- `GET /Curso/{codigo}` - Busca curso específico por código

### 📋 Currículos
- `GET /Curriculo?curso={codigo}` - Lista currículos de um curso
  - Query params:
    - `curso`: **Obrigatório** - Código do curso
    - `_count`: Quantidade de registros por página (padrão: 10)
    - `_offset`: Número de registros a pular
- `GET /Curriculo/{id}` - Busca currículo específico por ID (formato: "CODIGO.VERSAO" ex: "6351.2")
- `GET /Curriculo/{id}/disciplina` - Lista disciplinas de um currículo
  - Query params:
    - `tipo`: Tipo da disciplina (OBRIGATORIA, OPTATIVA)
    - `nome`: Nome da disciplina (busca parcial)
    - `_count`: Quantidade de registros por página (padrão: 10)
    - `_offset`: Número de registros a pular
- `GET /Curriculo/{id}/disciplina/{disciplina}` - Consulta disciplina específica de um currículo

## 🛠️ Comandos Úteis

```bash
# Ver logs
docker compose logs -f

# Parar os serviços  
docker compose down

# Resetar tudo (apaga dados)
docker compose down -v

# Reiniciar
docker compose restart
```

## 💡 Exemplos de Uso

```bash
# Buscar alunos com nome "robert"
curl "http://localhost:8000/Aluno?nome=robert"

# Buscar alunos do curso 6351 (Redes)
curl "http://localhost:8000/Aluno?curso=6351"

# Buscar alunos que ingressaram em 2020/1
curl "http://localhost:8000/Aluno?periodoIngresso=2020/1"

# Detalhes de um aluno específico
curl "http://localhost:8000/Aluno/180012345"

# Listar todos os cursos
curl "http://localhost:8000/Curso"

# Buscar cursos noturnos
curl "http://localhost:8000/Curso?turno=NOTURNO"

# Detalhes de um curso específico
curl "http://localhost:8000/Curso/6351"

# Currículos do curso 6351
curl "http://localhost:8000/Curriculo?curso=6351"

# Detalhes de um currículo específico
curl "http://localhost:8000/Curriculo/6351.2"

# Disciplinas obrigatórias de um currículo
curl "http://localhost:8000/Curriculo/6351.2/disciplina?tipo=OBRIGATORIA"

# Buscar disciplina específica em um currículo
curl "http://localhost:8000/Curriculo/6351.2/disciplina/ENE0022"
```

