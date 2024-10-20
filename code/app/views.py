from django.shortcuts import render, redirect
from django.views import View
from django.views.generic import ListView

from .forms import EmailLoginForm
from .models import EmailAccount
from .models import EmailMessage
from .tasks import fetch_emails


class EmailLoginView(View):
    template_name = 'app/email_login.html'
    form_class = EmailLoginForm

    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = self.form_class(request.POST)
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
        return render(request, self.template_name, {'form': form})


class MessageListView(ListView):
    model = EmailMessage
    template_name = 'app/message_list.html'
    context_object_name = 'messages'
    ordering = ['-send_date']
