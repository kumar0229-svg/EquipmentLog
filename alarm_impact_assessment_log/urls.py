from django.urls import path

from . import views

urlpatterns = [
    path('', views.placeholder, name='alarm_impact_assessment_log'),
]
