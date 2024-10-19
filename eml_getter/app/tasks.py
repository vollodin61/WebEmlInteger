import email
import imaplib
from email.policy import default

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.utils import timezone

from .models import EmailAccount, Message


def connect_to_mail(account):
    if 'yandex' in account.email:
        mail_server = 'imap.yandex.ru'
    elif 'gmail' in account.email:
        mail_server = 'imap.gmail.com'
    elif 'mail.ru' in account.email:
        mail_server = 'imap.mail.ru'
    else:
        raise ValueError('Unsupported email provider')

    mail = imaplib.IMAP4_SSL(mail_server)
    mail.login(account.email, account.password)
    mail.select('inbox')  # Выбираем папку "Входящие"

    return mail


def fetch_message_ids(mail):
    status, messages = mail.search(None, 'ALL')  # Ищем все письма
    email_ids = messages[0].split()
    return email_ids


def process_and_save_message(mail, email_id, channel_layer):
    status, data = mail.fetch(email_id, '(RFC822)')
    raw_email = data[0][1]

    msg = email.message_from_bytes(raw_email, policy=default)

    subject = msg.get('Subject', '(Без темы)')
    sent_at = msg.get('Date')
    body = ""
    attachments = []

    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8')
            if part.get_content_disposition() == 'attachment':
                filename = part.get_filename()
                if filename:
                    file_data = part.get_payload(decode=True)
                    attachments.append({
                        'filename': filename,
                        'content': file_data
                    })
    else:
        body = msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8')

    # Сохраняем сообщение в базу данных
    message = Message.objects.create(
        subject=subject,
        sent_at=sent_at,
        received_at=timezone.now(),
        body=body,
        attachments=attachments
    )

    # Отправляем сообщение через WebSocket
    async_to_sync(channel_layer.group_send)(
        "progress_group",
        {
            "type": "send_message",
            "message": {
                "subject": message.subject,
                "sent_at": message.sent_at.strftime("%Y-%m-%d %H:%M:%S"),
                "received_at": message.received_at.strftime("%Y-%m-%d %H:%M:%S"),
                "body": message.body
            }
        }
    )


@shared_task
def fetch_emails(account_id):
    account = EmailAccount.objects.get(id=account_id)
    mail = connect_to_mail(account)

    email_ids = fetch_message_ids(mail)
    total_emails = len(email_ids)

    channel_layer = get_channel_layer()

    for i, email_id in enumerate(email_ids):
        process_and_save_message(mail, email_id, channel_layer)

        # Отправляем прогресс в WebSocket
        async_to_sync(channel_layer.group_send)(
            "progress_group",
            {
                "type": "send_progress",
                "progress": int((i + 1) / total_emails * 100)
            }
        )

    mail.logout()
