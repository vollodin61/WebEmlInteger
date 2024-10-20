from django.shortcuts import render, redirect

from .forms import EmailLoginForm
from .models import EmailMessage, EmailAccount
from .tasks import fetch_emails


def message_list(request):
    messages = EmailMessage.objects.all()
    if not messages:
        account = EmailAccount.objects.first()
        if account:
            fetch_emails.delay(account.id)
    return render(request, 'app/message_list.html', {'messages': messages})


def email_login(request):
    if request.method == 'POST':
        form = EmailLoginForm(request.POST)
        if form.is_valid():
            account = form.cleaned_data['account']
            if account:
                account_id = account.id
            else:
                provider = form.cleaned_data['provider']
                email = form.cleaned_data['email']
                password = form.cleaned_data['password']

                account = EmailAccount.objects.create(
                    provider=provider,
                    email=email,
                    password=password
                )
                account_id = account.id

            fetch_emails.delay(account_id)

            return redirect('message_list')
    else:
        form = EmailLoginForm()
    return render(request, 'app/email_login.html', {'form': form})