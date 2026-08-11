from django.urls import path

from . import views

urlpatterns = [
    path('', views.placeholder, name='qa_review_sheet'),
]
