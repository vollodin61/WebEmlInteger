from django.urls import path

from .views import EmailLoginView, MessageListView, RefreshMessagesView

urlpatterns = [
    path('', EmailLoginView.as_view(), name='email_login'),
    path('messages/', MessageListView.as_view(), name='message_list'),
    path('refresh_messages/', RefreshMessagesView.as_view(), name='refresh_messages'),
]
