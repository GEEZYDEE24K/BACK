FROM python:3.12-slim

# Evita que Python escriba pyc y use buffers
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copiar sólo los archivos de dependencias para aprovechar cache
COPY backend_estudiantil/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Exponer el puerto en que corre FastAPI
EXPOSE 8000

# Comando de ejecución
CMD ["uvicorn", "backend_estudiantil.infrastructure.main:app", "--host", "0.0.0.0", "--port", "8000"]
