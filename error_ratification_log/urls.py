from django.urls import path

from . import views

urlpatterns = [
    path('', views.placeholder, name='error_ratification_log'),
]
