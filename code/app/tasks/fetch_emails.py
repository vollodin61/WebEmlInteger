import imaplib
import time

from celery import shared_task
from loguru import logger

from .email_processing import EmailFetcher
from .utils import handle_exception
from ..models import EmailAccount


@shared_task
def fetch_emails(account_id):
    try:
        account = EmailAccount.objects.get(id=account_id)
    except EmailAccount.DoesNotExist:
        logger.error(f"Аккаунт с ID {account_id} не найден.")
        return

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
            handle_exception(e)
            break
