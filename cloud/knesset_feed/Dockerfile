FROM python:3.14-slim
WORKDIR /app
COPY cloud/knesset_feed/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY bot/__init__.py bot/__init__.py
COPY bot/adapters/__init__.py bot/adapters/__init__.py
COPY bot/adapters/knesset/__init__.py bot/adapters/knesset/feed.py bot/adapters/knesset/
COPY bot/domain/__init__.py bot/domain/errors.py bot/domain/feed.py bot/domain/
COPY cloud/knesset_feed/app.py ./app.py
USER 65532:65532
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "4", "--timeout", "300", "app:app"]
