import email
import imaplib
import os
import time
from datetime import datetime
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime

from asgiref.sync import async_to_sync
from bs4 import BeautifulSoup  # Для обработки HTML-содержимого
from celery import shared_task
from channels.layers import get_channel_layer
from django.db.utils import IntegrityError
from loguru import logger

from .models import EmailAccount, EmailMessage

# Настройка логирования
# Удаляем все обработчики
logger.remove()

# Создаем директорию для логов, если ее нет
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Формируем имя файла
log_filename = datetime.now().strftime('%Y%m%d%H%M%S') + '.log'

# Настраиваем логирование
logger.add(
    os.path.join(log_dir, log_filename),
    rotation='2 MB',  # Ротация при достижении 2 MB
    retention=5,  # Хранить до 5 файлов
    compression=None,  # Без сжатия
    enqueue=True  # Для работы в многопоточном окружении
)


class EmailFetcher:
    def __init__(self, account):
        self.account = account
        self.provider = account.provider
        self.email_address = account.email
        self.password = account.password
        self.mail = None
        self.channel_layer = get_channel_layer()
        self.total_emails = 0
        self.is_searching = True  # Флаг для этапа поиска

    def connect(self):
        self.mail = imaplib.IMAP4_SSL('imap.' + self.provider)
        self.mail.login(self.email_address, self.password)
        self.mail.select('inbox')

    def disconnect(self):
        if self.mail:
            self.mail.logout()

    def fetch_email_uids(self):
        # Получаем последний UID из базы данных
        last_uid = (EmailMessage.objects
                    .filter(account=self.account)
                    .order_by('-uid')
                    .values_list('uid', flat=True)
                    .first())

        if last_uid:
            search_criteria = f'(UID {int(last_uid) + 1}:*)'
        else:
            search_criteria = 'ALL'

        # Ищем сообщения по UID
        result, data = self.mail.uid('search', None, search_criteria)
        email_uids = data[0].split()
        self.total_emails = len(email_uids)
        return email_uids

    def process_email(self, uid):
        result, message_data = self.mail.uid('fetch', uid, '(RFC822)')
        raw_email = message_data[0][1]
        email_message = email.message_from_bytes(raw_email)

        # Декодируем тему письма
        subject_header = email_message['Subject']
        subject = str(make_header(decode_header(subject_header)))

        # Парсим дату отправки
        send_date = email_message['Date']
        try:
            send_date = parsedate_to_datetime(send_date)
        except Exception as e:
            logger.error(f'Ошибка при парсинге даты: {e}')
            send_date = datetime.now()

        # Получаем Message-ID
        message_id = email_message.get('Message-ID')
        if not message_id:
            message_id = f"{uid.decode()}@{self.provider}"

        # Обрабатываем тело письма
        body = self.get_email_body(email_message)

        # Создаем объект EmailMessage
        try:
            email_message_obj = EmailMessage.objects.create(
                account=self.account,
                subject=subject,
                send_date=send_date,
                receive_date=send_date,
                body=body,
                message_id=message_id,
                uid=int(uid),
                is_new=True,  # Помечаем как новое сообщение
            )

            # Отправляем новое сообщение через WebSocket
            self.send_new_message(email_message_obj)

        except IntegrityError:
            logger.error(f"Сообщение с UID {uid} уже существует. Пропуск.")

    def get_email_body(self, email_message):
        body = ''
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get('Content-Disposition'))
                if 'attachment' not in content_disposition:
                    charset = part.get_content_charset()
                    payload = part.get_payload(decode=True)
                    if payload:
                        if charset:
                            payload = payload.decode(charset, errors='replace')
                        else:
                            payload = payload.decode('utf-8', errors='replace')
                        if content_type == 'text/plain':
                            body += payload
                        elif content_type == 'text/html':
                            soup = BeautifulSoup(payload, 'html.parser')
                            text = soup.get_text()
                            body += text
        else:
            charset = email_message.get_content_charset()
            payload = email_message.get_payload(decode=True)
            if payload:
                if charset:
                    payload = payload.decode(charset, errors='replace')
                else:
                    payload = payload.decode('utf-8', errors='replace')
                content_type = email_message.get_content_type()
                if content_type == 'text/plain':
                    body += payload
                elif content_type == 'text/html':
                    soup = BeautifulSoup(payload, 'html.parser')
                    text = soup.get_text()
                    body += text
        return body

    def update_progress(self, idx):
        if self.is_searching:
            message = f'Чтение сообщений {idx + 1}'
        else:
            message = f'Получение сообщений {idx + 1} из {self.total_emails}'

        progress = int((idx + 1) / self.total_emails * 100) if self.total_emails > 0 else 0
        async_to_sync(self.channel_layer.group_send)(
            'progress',
            {
                'type': 'progress_update',
                'message': {'progress': progress, 'status': message},
            }
        )

    def send_new_message(self, email_message_obj):
        async_to_sync(self.channel_layer.group_send)(
            'progress',
            {
                'type': 'new_message',
                'message': {
                    'id': email_message_obj.id,
                    'subject': email_message_obj.subject,
                    'send_date': email_message_obj.send_date.strftime('%d.%m.%Y %H:%M'),
                    'receive_date': email_message_obj.receive_date.strftime('%d.%m.%Y %H:%M'),
                    'body': email_message_obj.body[:50],
                },
            }
        )

    def fetch_and_process_emails(self):
        try:
            self.connect()
            self.is_searching = True  # Этап поиска
            # Если требуется реализовать поиск последнего сообщения на сервере, можно добавить логику здесь

            self.is_searching = False  # Этап загрузки новых сообщений
            email_uids = self.fetch_email_uids()
            for idx, uid in enumerate(email_uids):
                try:
                    self.process_email(uid)
                    self.update_progress(idx)
                    time.sleep(0.1)
                except Exception as e:
                    logger.error(f"Ошибка при обработке письма UID {uid}: {e}")
            self.disconnect()
            logger.info('Завершилось успешно')
        except imaplib.IMAP4.abort as e:
            logger.error(f"Соединение с сервером было прервано: {e}")
            raise e
        except Exception as e:
            logger.error(f"Ошибка при получении писем: {e}")
            raise e


@shared_task
def fetch_emails(account_id):
    account = EmailAccount.objects.get(id=account_id)
    max_retries = 3
    attempt = 0

    while attempt < max_retries:
        try:
            fetcher = EmailFetcher(account)
            fetcher.fetch_and_process_emails()
            break  # Успешно завершили
        except imaplib.IMAP4.abort as e:
            attempt += 1
            logger.error(f"Попытка переподключения {attempt} из {max_retries}...")
            time.sleep(5)
            if attempt == max_retries:
                logger.error("Превышено максимальное количество попыток переподключения.")
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            break
