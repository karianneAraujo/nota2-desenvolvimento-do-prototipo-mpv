FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY criar_banco.py ./criar_banco.py
COPY venv/templates ./venv/templates

EXPOSE 5000

CMD ["python", "-m", "app"]
