FROM python:3.11-slim

WORKDIR /app

# Instala dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia código y assets
COPY app.py .
COPY templates ./templates
COPY static ./static

EXPOSE 5000
CMD ["python", "app.py"]
