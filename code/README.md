# eml_getter

Проект для импортирования сообщений с почты с отображением прогресса.

## Технологии

- Django 4.2.16
- Django Channels 4.0.0
- Celery 5.4.0
- Redis
- PostgreSQL
- Docker и Docker Compose

## Установка и запуск

### Предварительные требования

- Docker
- Docker Compose

### Шаги установки

1. Клонируйте репозиторий:

    ```bash
    git clone https://github.com/yourusername/eml_getter.git
    cd eml_getter
    ```

2. Создайте файл .env при необходимости и настройте переменные окружения.

3. Запустите контейнеры Docker:
    ```bash
    docker-compose up --build
    ```
4. Выполните миграции и создайте суперпользователя:

    ```bash 
    docker-compose run web python manage.py migrate
    docker-compose run web python manage.py createsuperuser
    ```
5. Откройте приложение в браузере по адресу http://localhost:8000.

### Запуск через Gunicorn

Приложение настроено для запуска через Gunicorn с использованием UvicornWorker для поддержки ASGI:
```bash
gunicorn eml_getter.eml_getter.asgi:application -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```
### Логирование

Логи приложения сохраняются в папку logs/ в файле app.log.

### Мониторинг Celery

Flower доступен по адресу http://localhost:5555 для мониторинга задач Celery.

## Использование

1. Войдите в административную панель Django (/admin/) и добавьте учетные записи электронной почты.
2. Перейдите на главную страницу, и процесс получения сообщений начнется автоматически.
3. Прогресс-бар отобразит текущий статус процесса.