FROM python:3.12-alpine

WORKDIR /app
COPY server.py index.html ./

ENV HOST=0.0.0.0 PORT=8000 PYTHONUNBUFFERED=1
EXPOSE 8000

RUN adduser -D -H app && chown -R app /app
USER app

CMD ["python", "server.py"]
