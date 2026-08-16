from django.urls import path

from . import views

urlpatterns = [
    path('', views.entry_list, name='bmr_log'),
    path('print/', views.entry_list_print, name='bmr_entry_list_print'),
    path('new/', views.prepare_bmr, name='bmr_prepare'),
    path('pending-submission/', views.pending_submission, name='bmr_pending_submission'),
    path('<int:pk>/', views.entry_detail, name='bmr_entry_detail'),
    path('<int:pk>/receive/', views.verify_receive_bmr, name='bmr_verify_receive'),
    path('<int:pk>/issue/', views.mark_issued, name='bmr_mark_issued'),
    path('<int:pk>/return/', views.mark_returned, name='bmr_mark_returned'),
    path('<int:pk>/verify-return/', views.verify_return, name='bmr_verify_return'),
    path('<int:pk>/receive-back/', views.receive_back, name='bmr_receive_back'),
]
