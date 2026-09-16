# Dockerfile for Trueque Estudiantil backend
# Use official Python image (slim) without virtualenv
FROM python:3.12-slim

# Install OS dependencies (postgres client libraries)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install globally
COPY backend_estudiantil/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY backend_estudiantil ./backend_estudiantil

# Expose the default port
EXPOSE 8000

# Command to run the FastAPI app
CMD ["uvicorn", "backend_estudiantil.infrastructure.main:app", "--host", "0.0.0.0", "--port", "8000"]
