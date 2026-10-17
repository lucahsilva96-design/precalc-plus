FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN DJANGO_SECRET_KEY=build-placeholder DJANGO_DEBUG=False DJANGO_ALLOWED_HOSTS=localhost python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["sh", "-c", "gunicorn config.wsgi --bind 0.0.0.0:$PORT --workers 2"]
