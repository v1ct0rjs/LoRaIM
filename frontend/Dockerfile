FROM python:3.11-slim

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar dependencias e instalarlas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install gunicorn

# Copiar el código fuente
COPY app.py .
COPY templates ./templates
COPY static ./static

# Exponer el puerto por defecto del contenedor
EXPOSE 5000

# Ejecutar la app con Gunicorn, 4 workers y binding a 0.0.0.0
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]

