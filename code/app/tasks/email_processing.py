import email
import imaplib
import time
from datetime import datetime
from email.utils import parsedate_to_datetime

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.utils import IntegrityError
from loguru import logger

from ..models import EmailMessage
from .utils import decode_subject, get_email_body_content


class BaseEmailFetcher:
    """
    Родительский класс, отвечающий за подключение и отключение от почтового сервера.
    """

    def __init__(self, account):
        self.account = account
        self.provider = account.provider
        self.email_address = account.email
        self.password = account.password
        self.mail = None

    def connect(self):
        """
        Подключение к почтовому серверу.
        """
        self.mail = imaplib.IMAP4_SSL(f'imap.{self.provider}')
        self.mail.login(self.email_address, self.password)
        self.mail.select('inbox')

    def disconnect(self):
        """
        Отключение от почтового сервера.
        """
        if self.mail:
            self.mail.logout()


class EmailFetcher(BaseEmailFetcher):
    """
    Дочерний класс, отвечающий за обработку входящих сообщений.
    """

    def __init__(self, account):
        super().__init__(account)
        self.channel_layer = get_channel_layer()
        self.total_emails = 0
        self.is_searching = True  # Флаг для этапа поиска

    def fetch_email_uids(self):
        """
        Получение UID писем, которые нужно обработать.
        """
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
        """
        Обработка отдельного письма по UID.
        """
        result, message_data = self.mail.uid('fetch', uid, '(RFC822)')
        raw_email = message_data[0][1]
        email_message = email.message_from_bytes(raw_email)

        # Декодируем тему письма
        subject_header = email_message['Subject']
        subject = decode_subject(subject_header)

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
        body = get_email_body_content(email_message)

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

    def send_new_message(self, email_message_obj):
        """
        Отправка информации о новом сообщении через WebSocket.
        """
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

    def update_progress(self, idx):
        """
        Обновление прогресса обработки писем.
        """
        if self.is_searching:
            message = f'Чтение сообщений {idx + 1}'
        else:
            message = f'Получение сообщений {idx + 1} из {self.total_emails}'

        progress = int((
                                   idx + 1) / self.total_emails * 100) if self.total_emails > 0 else 100  # Устанавливаем 100%, если нет новых сообщений
        async_to_sync(self.channel_layer.group_send)(
            'progress',
            {
                'type': 'progress_update',
                'message': {'progress': progress, 'status': message},
            }
        )

    def fetch_and_process_emails(self):
        """
        Основной метод для получения и обработки писем.
        """
        try:
            self.connect()
            self.is_searching = True  # Этап поиска

            self.is_searching = False  # Этап загрузки новых сообщений
            email_uids = self.fetch_email_uids()
            if self.total_emails == 0:
                # Нет новых сообщений, отправляем финальное обновление прогресса
                async_to_sync(self.channel_layer.group_send)(
                    'progress',
                    {
                        'type': 'progress_update',
                        'message': {'progress': 100, 'status': 'Все сообщения получены'},
                    }
                )
            else:
                for idx, uid in enumerate(email_uids):
                    try:
                        self.process_email(uid)
                        self.update_progress(idx)
                        time.sleep(0.1)
                    except Exception as e:
                        logger.error(f"Ошибка при обработке письма UID {uid}: {e}")
                # После обработки всех сообщений, отправляем финальное обновление прогресса
                async_to_sync(self.channel_layer.group_send)(
                    'progress',
                    {
                        'type': 'progress_update',
                        'message': {'progress': 100, 'status': 'Все сообщения получены'},
                    }
                )
            self.disconnect()
            logger.info('Завершилось успешно')
        except imaplib.IMAP4.abort as e:
            logger.error(f"Соединение с сервером было прервано: {e}")
            raise e
        except Exception as e:
            logger.error(f"Ошибка при получении писем: {e}")
            raise e
