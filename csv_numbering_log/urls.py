from django.urls import path

from . import views

urlpatterns = [
    path('', views.placeholder, name='csv_numbering_log'),
]
