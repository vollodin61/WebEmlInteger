from django.urls import path

from . import views

urlpatterns = [
    path('', views.email_login, name='email_login'),
    path('messages/', views.message_list, name='message_list'),
]
