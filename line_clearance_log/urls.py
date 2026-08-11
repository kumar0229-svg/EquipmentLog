from django.urls import path

from . import views

urlpatterns = [
    path('', views.placeholder, name='line_clearance_log'),
]
