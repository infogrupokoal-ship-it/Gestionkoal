FROM python:3.10-slim-buster

WORKDIR /app

# Evita bytecode y fuerza stdout sin buffer
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Usuario no root
RUN adduser --disabled-password --gecos '' appuser \
 && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000
ENV FLASK_APP=backend:create_app \
    FLASK_ENV=production

# Respeta $PORT si existe, cae a 5000 si no
CMD ["sh", "-c", "waitress-serve --host=0.0.0.0 --port=${PORT:-5000} --threads=4 --call backend:create_app"]