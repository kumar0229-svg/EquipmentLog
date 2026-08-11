from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

admin.site.site_header = 'DigiLog Administration'
admin.site.site_title = 'DigiLog'
admin.site.index_title = 'DigiLog Administration'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('equipment/', include('masters.urls')),
    path('equipment-log/', include('activitylog.urls')),
    path('bmr-log/', include('bmr_log.urls')),
    path('cleaning-record-log/', include('cleaning_record_log.urls')),
    path('qualification-protocol-log/', include('qualification_protocol_log.urls')),
    path('vmp-schedule/', include('vmp_schedule.urls')),
    path('line-clearance-log/', include('line_clearance_log.urls')),
    path('qa-review-sheet/', include('qa_review_sheet.urls')),
    path('error-ratification-log/', include('error_ratification_log.urls')),
    path('data-entry-error-log/', include('data_entry_error_log.urls')),
    path('csv-numbering-log/', include('csv_numbering_log.urls')),
    path('alarm-impact-assessment-log/', include('alarm_impact_assessment_log.urls')),
    path('', include('core.urls')),
]
