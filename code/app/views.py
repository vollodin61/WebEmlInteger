from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views import View
from django.views.generic import ListView

from .forms import EmailLoginForm
from .models import EmailAccount, EmailMessage
from .tasks import fetch_emails


class EmailLoginView(View):
    template_name = 'app/email_login.html'
    form_class = EmailLoginForm

    def get(self, request):
        form = self.form_class()
        show_new = request.GET.get('show_new', 'false') == 'true'
        return render(request, self.template_name, {'form': form, 'show_new': show_new})

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            account = form.cleaned_data.get('account')
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

    def get_queryset(self):
        queryset = super().get_queryset()
        show_new = self.request.GET.get('show_new', 'false') == 'true'
        if show_new:
            queryset = queryset.filter(is_new=True)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['show_new'] = self.request.GET.get('show_new', 'false') == 'true'
        return context


class RefreshMessagesView(View):
    def get(self, request):
        account = EmailAccount.objects.first()  # Получаем первый аккаунт, измените при необходимости
        if account:
            # Сбрасываем флаг is_new для существующих сообщений
            EmailMessage.objects.filter(account=account).update(is_new=False)
            fetch_emails.delay(account.id)
            return JsonResponse({'status': 'ok'})
        return JsonResponse({'status': 'error'}, status=400)
