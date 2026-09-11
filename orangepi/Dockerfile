FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends iproute2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY cli.py entrypoint.sh ./
RUN mkdir -p app/data app/updates && chmod +x entrypoint.sh

EXPOSE 8000

CMD ["./entrypoint.sh"]
