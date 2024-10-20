from django.db import models


class EmailAccount(models.Model):
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=256)
    provider = models.CharField(max_length=50)

    def __str__(self):
        return self.email


class EmailMessage(models.Model):
    account = models.ForeignKey(EmailAccount, on_delete=models.CASCADE)
    subject = models.CharField(max_length=255)
    send_date = models.DateTimeField()
    receive_date = models.DateTimeField()
    body = models.TextField()
    message_id = models.CharField(max_length=255, unique=True)
    uid = models.IntegerField(unique=True, null=True, blank=True)
    is_new = models.BooleanField(default=False)

    def __str__(self):
        return self.subject


class Attachment(models.Model):
    file = models.FileField(upload_to='attachments/')
    message = models.ForeignKey(EmailMessage, on_delete=models.CASCADE)

    def __str__(self):
        return self.file.name
