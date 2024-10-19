from django.contrib import admin
from .models import EmailAccount, EmailMessage, Attachment

admin.site.register(Attachment)
admin.site.register(EmailMessage)
admin.site.register(EmailAccount)
