from django.urls import path

from . import views

urlpatterns = [
    path('', views.placeholder, name='qualification_protocol_log'),
]
