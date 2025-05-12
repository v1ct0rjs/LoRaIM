FROM python:3.9-slim-bullseye
COPY requirements.txt requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
# Comando para ejecutar la aplicación cuando el contenedor inicie
# Usaremos gunicorn como un servidor WSGI más robusto para producción
# Si no quieres instalar gunicorn, puedes usar: CMD ["python3", "app.py"]
# Pero gunicorn es recomendado. Añádelo a requirements.txt si lo usas.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
# Por simplicidad, usaremos el servidor de desarrollo de Flask por ahora,
# pero ten en cuenta que NO es para producción.
# CMD ["python3", "app.py"]