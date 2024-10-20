import email
import imaplib
import time
from datetime import datetime
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.db.utils import IntegrityError
from loguru import logger as lg

from .models import EmailAccount, EmailMessage

ilg = lg.info
elg = lg.error


class EmailFetcher:
    def __init__(self, account):
        self.account = account
        self.provider = account.provider
        self.email_address = account.email
        self.password = account.password
        self.mail = None
        self.channel_layer = get_channel_layer()
        self.total_emails = 0

    def connect(self):
        self.mail = imaplib.IMAP4_SSL('imap.' + self.provider)
        self.mail.login(self.email_address, self.password)
        self.mail.select('inbox')

    def disconnect(self):
        if self.mail:
            self.mail.logout()

    def fetch_email_ids(self):
        result, data = self.mail.search(None, 'ALL')
        email_ids = data[0].split()
        self.total_emails = len(email_ids)
        return email_ids

    def process_email(self, email_id):
        result, message_data = self.mail.fetch(email_id, '(RFC822)')
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
            elg(f'Ошибка при парсинге даты: {e}')
            send_date = datetime.now()

        # Получаем Message-ID
        message_id = email_message.get('Message-ID')
        if not message_id:
            message_id = f"{email_id.decode()}@{self.provider}"

        # Обрабатываем тело письма
        body = self.get_email_body(email_message)

        # Создаем объект EmailMessage
        try:
            # Сохраняем созданный объект в переменную email_message_obj
            email_message_obj = EmailMessage.objects.create(
                account=self.account,
                subject=subject,
                send_date=send_date,
                receive_date=send_date,
                body=body,
                message_id=message_id,
            )

            # Отправляем новое сообщение через WebSocket
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

        except IntegrityError:
            elg(f"Сообщение с ID {message_id} уже существует. Пропуск.")

    def get_email_body(self, email_message):
        body = ''
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get('Content-Disposition'))
                if content_type == 'text/plain' and 'attachment' not in content_disposition:
                    charset = part.get_content_charset()
                    payload = part.get_payload(decode=True)
                    if payload:
                        if charset:
                            body += payload.decode(charset, errors='replace')
                        else:
                            body += payload.decode('utf-8', errors='replace')
        else:
            charset = email_message.get_content_charset()
            payload = email_message.get_payload(decode=True)
            if payload:
                if charset:
                    body = payload.decode(charset, errors='replace')
                else:
                    body = payload.decode('utf-8', errors='replace')
        return body

    def update_progress(self, idx):
        progress = int((idx + 1) / self.total_emails * 100)
        async_to_sync(self.channel_layer.group_send)(
            'progress',
            {
                'type': 'progress_update',
                'message': {'progress': progress},
            }
        )

    def fetch_and_process_emails(self):
        try:
            self.connect()
            email_ids = self.fetch_email_ids()
            for idx, email_id in enumerate(email_ids):
                try:
                    self.process_email(email_id)
                    self.update_progress(idx)
                    time.sleep(0.1)
                except Exception as e:
                    elg(f"Ошибка при обработке письма {email_id}: {e}")
            self.disconnect()
            ilg('Завершилось успешно')
        except imaplib.IMAP4.abort as e:
            elg(f"Соединение с сервером было прервано: {e}")
            raise e
        except Exception as e:
            elg(f"Ошибка при получении писем: {e}")
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
            lg.error(f"Попытка переподключения {attempt} из {max_retries}...")
            time.sleep(5)
            if attempt == max_retries:
                lg.error("Превышено максимальное количество попыток переподключения.")
        except Exception as e:
            lg.error(f"Ошибка: {e}")
            break



# @shared_task
# def fetch_emails(account_id):
#     account = EmailAccount.objects.get(id=account_id)
#     provider = account.provider
#     email_address = account.email
#     password = account.password
#
#     max_retries = 3
#     attempt = 0
#
#     while attempt < max_retries:
#         try:
#             mail = imaplib.IMAP4_SSL('imap.' + provider)
#             mail.login(email_address, password)
#             mail.select('inbox')
#             result, data = mail.search(None, 'ALL')
#             email_ids = data[0].split()
#             total_emails = len(email_ids)
#             channel_layer = get_channel_layer()
#
#             for idx, email_id in enumerate(email_ids):
#                 try:
#                     result, message_data = mail.fetch(email_id, '(RFC822)')
#                     raw_email = message_data[0][1]
#                     email_message = email.message_from_bytes(raw_email)
#
#                     # Декодируем тему письма
#                     subject_header = email_message['Subject']
#                     subject = str(make_header(decode_header(subject_header)))
#
#                     # Парсим дату отправки
#                     send_date = email_message['Date']
#                     try:
#                         send_date = parsedate_to_datetime(send_date)
#                     except Exception as e:
#                         elg(f'Ошибка при парсинге даты: {e}')
#                         send_date = datetime.now()
#
#                     # Получаем Message-ID
#                     message_id = email_message.get('Message-ID')
#                     if not message_id:
#                         # Если Message-ID отсутствует, создаём свой уникальный идентификатор
#                         message_id = f"{email_id.decode()}@{provider}"
#
#                     # Обрабатываем тело письма
#                     body = ''
#                     if email_message.is_multipart():
#                         for part in email_message.walk():
#                             content_type = part.get_content_type()
#                             content_disposition = str(part.get('Content-Disposition'))
#                             if content_type == 'text/plain' and 'attachment' not in content_disposition:
#                                 charset = part.get_content_charset()
#                                 payload = part.get_payload(decode=True)
#                                 if payload:
#                                     if charset:
#                                         body += payload.decode(charset, errors='replace')
#                                     else:
#                                         body += payload.decode('utf-8', errors='replace')
#                     else:
#                         charset = email_message.get_content_charset()
#                         payload = email_message.get_payload(decode=True)
#                         if payload:
#                             if charset:
#                                 body = payload.decode(charset, errors='replace')
#                             else:
#                                 body = payload.decode('utf-8', errors='replace')
#
#                     # Создаем объект EmailMessage
#                     try:
#                         EmailMessage.objects.create(
#                             account=account,
#                             subject=subject,
#                             send_date=send_date,
#                             receive_date=send_date,
#                             body=body,
#                             message_id=message_id,  # Сохраняем Message-ID
#                         )
#                     except IntegrityError:
#                         # Если запись с таким Message-ID уже существует, пропускаем её
#                         elg(f"Сообщение с ID {message_id} уже существует. Пропуск.")
#
#                     # Обновляем прогресс
#                     progress = int((idx + 1) / total_emails * 100)
#                     async_to_sync(channel_layer.group_send)(
#                         'progress',
#                         {
#                             'type': 'progress_update',
#                             'message': {'progress': progress},
#                         }
#                     )
#                     time.sleep(0.1)
#                 except Exception as e:
#                     elg(f"Ошибка при обработке письма {email_id}: {e}")
#
#             # Отправляем уведомление о завершении
#             async_to_sync(channel_layer.group_send)(
#                 'progress',
#                 {
#                     'type': 'progress_update',
#                     'message': {'progress': 100, 'status': 'completed'},
#                 }
#             )
#             mail.logout()
#             elg('Завершилось успешно')
#             break  # Выходим из цикла, если успешно завершили работу
#
#         except imaplib.IMAP4.abort as e:
#             attempt += 1
#             elg(f"Соединение с сервером было прервано: {e}. Попытка переподключения {attempt} из {max_retries}...")
#             time.sleep(5)  # Ждем 5 секунд перед повторной попыткой
#             if attempt == max_retries:
#                 elg("Превышено максимальное количество попыток переподключения.")
#                 # Здесь можно отправить уведомление или выполнить другие действия
#
#         except Exception as e:
#             elg(f"Ошибка при получении писем: {e}")
#             break  # Выходим из цикла при других исключениях
