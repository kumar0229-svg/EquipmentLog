from django.urls import path

from . import views

urlpatterns = [
    path('', views.main_menu, name='main_menu'),
    path('module/<slug:slug>/', views.module_placeholder, name='module_placeholder'),
]
