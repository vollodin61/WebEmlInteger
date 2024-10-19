FROM python:3.12.5-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/code

WORKDIR /code

COPY requirements.txt /code/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /code/

RUN python manage.py collectstatic --noinput

CMD ["gunicorn", "eml_getter.asgi:application", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
