# app/tasks.py
import email
import imaplib
import time

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer

from .models import EmailAccount, EmailMessage


@shared_task
def fetch_emails(account_id):
    account = EmailAccount.objects.get(id=account_id)
    provider = account.provider
    email_address = account.email
    password = account.password

    try:
        mail = imaplib.IMAP4_SSL('imap.' + provider)
        mail.login(email_address, password)
        mail.select('inbox')

        result, data = mail.search(None, 'ALL')
        email_ids = data[0].split()
        total_emails = len(email_ids)
        channel_layer = get_channel_layer()

        for idx, email_id in enumerate(email_ids):
            result, message_data = mail.fetch(email_id, '(RFC822)')
            raw_email = message_data[0][1]
            email_message = email.message_from_bytes(raw_email)

            subject = email_message['Subject']
            send_date = email_message['Date']
            body = ''
            if email_message.is_multipart():
                for part in email_message.walk():
                    if part.get_content_type() == 'text/plain':
                        body += part.get_payload(decode=True).decode()
            else:
                body = email_message.get_payload(decode=True).decode()

            EmailMessage.objects.create(
                account=account,
                subject=subject,
                send_date=send_date,
                receive_date=send_date,
                body=body,
            )

            progress = int((idx + 1) / total_emails * 100)
            async_to_sync(channel_layer.group_send)(
                'progress',
                {
                    'type': 'progress_update',
                    'message': {'progress': progress},
                }
            )
            time.sleep(0.1)

        async_to_sync(channel_layer.group_send)(
            'progress',
            {
                'type': 'progress_update',
                'message': {'progress': 100, 'status': 'completed'},
            }
        )
        mail.logout()
    except Exception as e:
        print(f"Ошибка при получении писем: {e}")
