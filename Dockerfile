FROM python:3.11-slim

WORKDIR /app

# Instala dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia arquivos da aplicação
COPY fastapi_app.py .
COPY queries.py .
COPY models.py .

# Expõe porta
EXPOSE 8000

# Executa a aplicação
CMD ["uvicorn", "fastapi_app:app", "--host", "0.0.0.0", "--port", "8000"]