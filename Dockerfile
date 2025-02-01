FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .
COPY --chown=root:root . .
RUN rm -f .env

CMD ["python", "-u", "main.py"]