FROM python:3.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /opt/commandwise
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/* \
    && useradd --system --uid 10001 --no-create-home search \
    && mkdir /state && chown search:search /state
COPY search/requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt
COPY search/ ./search/
COPY corpus/ ./corpus/
USER search
WORKDIR /opt/commandwise/search
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
