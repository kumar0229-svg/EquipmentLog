from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('entries/', views.entry_list, name='entry_list'),
    path('entries/new/', views.start_activity, name='start_activity'),
    path('entries/<int:pk>/', views.entry_detail, name='entry_detail'),
    path('entries/<int:pk>/stop/', views.stop_activity, name='stop_activity'),
]
