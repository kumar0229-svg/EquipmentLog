from django.urls import path

from . import views

urlpatterns = [
    path('', views.main_menu, name='main_menu'),
    path('help/', views.help_page, name='help_page'),
    path('module/<slug:slug>/', views.module_placeholder, name='module_placeholder'),
]
