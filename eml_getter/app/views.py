from django.shortcuts import render

from .models import EmailAccount
from .tasks import fetch_emails


def message_list(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        account, created = EmailAccount.objects.get_or_create(email=email)
        if created:
            account.password = password
            account.save()

        fetch_emails.delay(account.id)

    return render(request, 'messages_list.html')
