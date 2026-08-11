from django.urls import path

from . import views

urlpatterns = [
    path('', views.placeholder, name='cleaning_record_log'),
]
