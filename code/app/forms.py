from django import forms

from .models import EmailAccount


class EmailLoginForm(forms.Form):
    account = forms.ModelChoiceField(
        queryset=EmailAccount.objects.all(),
        required=False,
        label='Выберите существующий аккаунт',
        empty_label='-- Новый аккаунт --'
    )
    provider = forms.CharField(label='Провайдер', max_length=50, required=False)
    email = forms.EmailField(label='Email', max_length=254, required=False)
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput, required=False)

    def clean(self):
        cleaned_data = super().clean()
        account = cleaned_data.get('account')
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')
        provider = cleaned_data.get('provider')

        if not account and not (provider and email and password):
            raise forms.ValidationError('Укажите существующий аккаунт или введите новые учетные данные.')

        return cleaned_data
