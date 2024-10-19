from django.shortcuts import render

from .models import EmailMessage, EmailAccount
from .tasks import fetch_emails


def message_list(request):
    messages = EmailMessage.objects.all()
    if not messages:
        # Запускаем задачу по получению писем
        account = EmailAccount.objects.first()
        if account:
            fetch_emails.delay(account.id)
    return render(request, 'app/message_list.html', {'messages': messages})
