FROM odoo:18.0

USER root
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONUTF8=1
ENV PYTHONIOENCODING=UTF-8
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir --break-system-packages -r requirements.txt

COPY . .

CMD ["sh", "-c", "python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${AI_UVICORN_WORKERS:-4}"]
