from django.urls import path

from . import views

urlpatterns = [
    path('', views.entry_list, name='bmr_log'),
    path('print/', views.entry_list_print, name='bmr_entry_list_print'),
    path('new/', views.issue_bmr, name='bmr_issue'),
    path('<int:pk>/', views.entry_detail, name='bmr_entry_detail'),
]
