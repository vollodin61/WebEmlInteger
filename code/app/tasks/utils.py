from email.header import decode_header, make_header
from bs4 import BeautifulSoup
from loguru import logger
from django.core.mail import send_mail
from django.conf import settings


def decode_subject(subject_header):
    """
    Декодирование заголовка темы письма.
    """
    try:
        return str(make_header(decode_header(subject_header)))
    except Exception as e:
        logger.error(f'Ошибка декодирования темы: {e}')
        return 'Без темы'


def get_email_body_content(email_message):
    """
    Извлечение текстового содержимого из письма.
    """
    body = ''
    if email_message.is_multipart():
        for part in email_message.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get('Content-Disposition'))
            if 'attachment' not in content_disposition:
                charset = part.get_content_charset()
                payload = part.get_payload(decode=True)
                if payload:
                    try:
                        if charset:
                            payload = payload.decode(charset, errors='replace')
                        else:
                            payload = payload.decode('utf-8', errors='replace')
                    except Exception as e:
                        logger.error(f'Ошибка декодирования части письма: {e}')
                        payload = 'Не удалось декодировать содержимое.'
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
            try:
                if charset:
                    payload = payload.decode(charset, errors='replace')
                else:
                    payload = payload.decode('utf-8', errors='replace')
            except Exception as e:
                logger.error(f'Ошибка декодирования письма: {e}')
                payload = 'Не удалось декодировать содержимое.'
            content_type = email_message.get_content_type()
            if content_type == 'text/plain':
                body += payload
            elif content_type == 'text/html':
                soup = BeautifulSoup(payload, 'html.parser')
                text = soup.get_text()
                body += text
    return body


def handle_exception(exception):
    """
    Централизованная обработка исключений.
    """
    # Логируем исключение с его трассировкой
    logger.exception(f"Произошла ошибка: {exception}")

    # Пример отправки уведомления по электронной почте
    subject = "Ошибка в приложении EML Getter"
    message = f"Произошла ошибка:\n\n{exception}"
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [settings.ADMIN_EMAIL]

    try:
        send_mail(subject, message, from_email, recipient_list)
    except Exception as email_exception:
        logger.error(f"Не удалось отправить уведомление об ошибке: {email_exception}")
