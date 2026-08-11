from django.urls import path

from activitylog import views as activitylog_views

urlpatterns = [
    path('', activitylog_views.dashboard, {'heading': 'EqStatus'}, name='main_menu'),
]
