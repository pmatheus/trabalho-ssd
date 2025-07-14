# SIGAA API - Trabalho 2

API REST para acesso aos dados do sistema SIGAA, implementada com FastAPI e PostgreSQL.

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
   ```cmd
   docker --version
   ```

## 🚀 Como Executar

1. **Clone o repositório e entre na pasta do trabalho2:**
   ```bash
   cd trabalho2
   ```

2. **Inicie os serviços:**
   ```bash
   docker compose up -d
   ```
   
   Aguarde cerca de 30 segundos na primeira execução para o banco ser criado e populado.

3. **Acesse a API:**
   - Documentação interativa: http://localhost:8000/docs
   - API base: http://localhost:8000

## 📊 Endpoints Disponíveis

### Alunos
- `GET /Aluno` - Lista alunos (params: `nome`, `curso`, `periodoIngresso`, `_count`, `_offset`)
- `GET /Aluno/{matricula}` - Busca aluno por matrícula

### Cursos  
- `GET /Curso` - Lista cursos (params: `nome`, `grau`, `turno`, `modalidade`, `_count`, `_offset`)
- `GET /Curso/{codigo}` - Busca curso por código

### Disciplinas
- `GET /Disciplina` - Lista disciplinas (params: `nome`, `codigo`, `unidade`, `modalidade`, `cargaHorariaMin`, `cargaHorariaMax`, `_count`, `_offset`)
- `GET /Disciplina/{codigo}` - Busca disciplina por código

### Currículos
- `GET /Curriculo?curso={codigo}` - Lista currículos de um curso (param obrigatório: `curso`)
- `GET /Curriculo/{id}` - Busca currículo por ID (ex: "6351.2")

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
# Buscar alunos do curso 6351
curl "http://localhost:8000/Aluno?curso=6351"

# Buscar disciplinas com "algoritmo" no nome
curl "http://localhost:8000/Disciplina?nome=algoritmo"

# Detalhes de um aluno
curl "http://localhost:8000/Aluno/180012345"

# Currículos do curso 6351
curl "http://localhost:8000/Curriculo?curso=6351"
```

## 🐛 Solução de Problemas

### Porta em uso
Se as portas 5432 ou 8000 já estiverem em uso, pare os processos ou edite as portas no `docker-compose.yml`.

### Reset completo
```bash
docker compose down -v
docker compose up -d
```