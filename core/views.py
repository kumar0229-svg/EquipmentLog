from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

# Single source of truth for the landing page's module grid — each entry
# doubles as the placeholder page's title lookup, so the tile and its
# destination never drift apart. A module with `url_name` set already has a
# real destination; left unset, its tile links to the shared "coming soon"
# placeholder instead.
MODULES = [
    # ---- Logs ---------------------------------------------------------
    {'key': 'equipment-log', 'title': 'Equipment Log', 'group': 'logs', 'url_name': 'dashboard',
     'description': 'Live equipment status by stream.'},
    {'key': 'bmr-log', 'title': 'BMR Issuance Log', 'group': 'logs', 'url_name': 'bmr_log',
     'description': 'Batch manufacturing record issuance.'},
    {'key': 'ecr-log', 'title': 'ECR Log', 'group': 'logs', 'url_name': 'cleaning_record_log',
     'description': 'Equipment cleaning records.'},
    {'key': 'qualification-protocol-log', 'title': 'Qualification Protocol Issuance Log', 'group': 'logs',
     'url_name': 'qualification_protocol_log', 'description': 'Protocol issuance for equipment qualification.'},
    {'key': 'vmp-schedule', 'title': 'VMP Schedule', 'group': 'logs', 'url_name': 'vmp_schedule',
     'description': 'Validation master plan scheduling.'},
    {'key': 'line-clearance-log', 'title': 'Line Clearance Log', 'group': 'logs', 'url_name': 'line_clearance_log',
     'description': 'Line clearance verification records.'},
    {'key': 'error-ratification-log', 'title': 'Error Ratification Log', 'group': 'logs',
     'url_name': 'error_ratification_log', 'description': 'Ratification of documentation errors.'},
    {'key': 'data-entry-error-log', 'title': 'Data Entry Error Log', 'group': 'logs',
     'url_name': 'data_entry_error_log', 'description': 'Data entry corrections register.'},
    {'key': 'csv-numbering-log', 'title': 'CSV Numbering Log', 'group': 'logs', 'url_name': 'csv_numbering_log',
     'description': 'Computer system validation document numbering.'},
    {'key': 'alarm-impact-assessment-log', 'title': 'Alarm Impact Assessment Log', 'group': 'logs',
     'url_name': 'alarm_impact_assessment_log', 'description': 'Impact assessment for critical alarms.'},
    {'key': 'nitrosamine-assessment-issuance-log', 'title': 'Nitrosamine Assessment Issuance Log', 'group': 'logs',
     'description': 'Issuance register for nitrosamine risk assessments.'},
    {'key': 'sop-amendment-log', 'title': 'SOP Amendment Log', 'group': 'logs',
     'description': 'Tracks changes made to SOPs.'},
    {'key': 'fmeca-log', 'title': 'FMECA Log', 'group': 'logs',
     'description': 'Failure mode, effects & criticality analysis, with periodic review.'},
    {'key': 'risk-assessment-log', 'title': 'Risk Assessment Log', 'group': 'logs',
     'description': 'Scheduled risk assessments.'},
    {'key': 'qualification-number-issuance-log', 'title': 'Qualification Number Issuance Log', 'group': 'logs',
     'description': 'Numbering for HVAC, equipment and area qualification.'},
    {'key': 'process-validation-log', 'title': 'Process Validation Log', 'group': 'logs',
     'description': 'Process validation protocol records.'},
    {'key': 'cleaning-validation-log', 'title': 'Cleaning Validation Log', 'group': 'logs',
     'description': 'Cleaning validation protocol records.'},
    {'key': 'study-protocol-log', 'title': 'Study Protocol Log', 'group': 'logs',
     'description': 'Study protocol issuance and tracking.'},
    {'key': 'software-incident-log', 'title': 'Software Incident Log', 'group': 'logs',
     'description': 'Computerised system incident register.'},

    # ---- Forms ----------------------------------------------------------
    {'key': 'qa-review-sheet', 'title': 'QA Review Sheet', 'group': 'forms', 'url_name': 'qa_review_sheet',
     'description': 'QA review checklist for issued documents.'},
    {'key': 'lms-audit-trail-form', 'title': 'LMS Audit Trail Form', 'group': 'forms',
     'description': 'Audit trail review for the LMS.'},
    {'key': 'line-clearance-form', 'title': 'Line Clearance Form', 'group': 'forms',
     'description': 'Line clearance checklist.'},
    {'key': 'error-ratification-form', 'title': 'Error Ratification Form', 'group': 'forms',
     'description': 'Error ratification request form.'},
]


def _resolve(module):
    if module.get('url_name'):
        return {**module, 'url': reverse(module['url_name']), 'available': True}
    return {**module, 'url': reverse('module_placeholder', args=[module['key']]), 'available': False}


def _greeting():
    hour = timezone.localtime().hour
    if hour < 12:
        return 'Good morning'
    if hour < 17:
        return 'Good afternoon'
    return 'Good evening'


def main_menu(request):
    modules = [_resolve(m) for m in MODULES]
    active_filter = request.GET.get('filter')
    if active_filter not in ('logs', 'forms'):
        active_filter = 'all'
    if active_filter != 'all':
        modules = [m for m in modules if m['group'] == active_filter]

    return render(
        request,
        'main_menu.html',
        {
            'greeting': _greeting(),
            'active_filter': active_filter,
            'modules': modules,
            'log_count': sum(1 for m in MODULES if m['group'] == 'logs'),
            'form_count': sum(1 for m in MODULES if m['group'] == 'forms'),
        },
    )


def module_placeholder(request, slug):
    module = next((m for m in MODULES if m['key'] == slug), None)
    title = module['title'] if module else slug.replace('-', ' ').title()
    return render(request, 'placeholder.html', {'title': title})
