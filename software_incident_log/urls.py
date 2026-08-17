from django.urls import path

from . import views

urlpatterns = [
    path('', views.entry_list, name='software_incident_log'),
    path('print/', views.entry_list_print, name='software_incident_log_print'),
    path('new/', views.log_incident, name='software_incident_log_new'),
    path('close/', views.select_incident_to_close, name='software_incident_log_select_close'),
    path('<int:pk>/closeout/', views.closeout, name='software_incident_log_closeout'),
]
