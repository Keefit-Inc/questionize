# syntax=docker/dockerfile:1
# Internal AI service. Reached only by Rails on the private Docker network.
FROM docker.io/library/python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY questionize ./questionize

RUN useradd --system --uid 1000 app
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "questionize.app:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
