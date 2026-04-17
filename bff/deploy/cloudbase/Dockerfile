FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONUTF8=1
ENV PYTHONIOENCODING=UTF-8

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY app /app/app
COPY migrations /app/migrations
COPY scripts/start_cloudbase.sh /app/scripts/start_cloudbase.sh
RUN chmod +x /app/scripts/start_cloudbase.sh

EXPOSE 8080

CMD ["/app/scripts/start_cloudbase.sh"]
