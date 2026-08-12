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

    # ---- Scheduler --------------------------------------------------------
    {'key': 'vmp-schedule', 'title': 'VMP Schedule', 'group': 'schedulers', 'url_name': 'vmp_schedule',
     'description': 'Validation master plan scheduling.'},
    {'key': 'list-of-schedules', 'title': 'List of Schedules', 'group': 'schedulers',
     'description': 'Master list of all department schedules, by frequency.'},

    # ---- Analytics ----------------------------------------------------------
    {'key': 'analytics', 'title': 'Analytics', 'group': 'analytics',
     'description': 'Usage and performance analytics across modules.'},
]

# Master list of schedules (1023-Q-0001/L4), grouped for the "List of
# Schedules" placeholder. Frequency labels are normalized to a small set of
# canonical buckets so near-duplicate source wording (Annually / Yearly /
# Yearly once) lists together.
_FREQUENCY_ALIASES = {
    'annually': 'Yearly',
    'yearly': 'Yearly',
    'yearly once': 'Yearly',
    'half yearly': 'Half Yearly',
    'yearly & 2-yearly': 'Yearly & 2-Yearly',
    '2 years once': '2 Years Once',
    '3 years once': '3 Years Once',
    'quarterly': 'Quarterly',
    'monthly': 'Monthly',
    'fortnightly': 'Fortnightly',
    'daily': 'Daily',
    'as per schedule': 'As Per Schedule',
}
FREQUENCY_ORDER = [
    'Daily', 'Fortnightly', 'Monthly', 'Quarterly', 'Half Yearly', 'Yearly',
    'Yearly & 2-Yearly', '2 Years Once', '3 Years Once', 'As Per Schedule',
]
SCHEDULES = [
    (1, 'QA', 'VMP Schedule', 'SH/26/001', 'As per schedule'),
    (2, 'API I', 'Schedule for fumigation of area', 'SH/26/002', 'half yearly'),
    (3, 'API I', 'Schedule for quarterly trending of critical alarms for 2026', 'SH/26/003', 'Quarterly'),
    (4, 'API I', 'Schedule for sieve screen verification API-1', 'SH/26/004', 'half yearly'),
    (5, 'API I', 'Schedule for magnetic grill verification API-1', 'SH/26/005', '3 years once'),
    (6, 'QA', 'APQR Schedule', 'SH/26/006', 'As per schedule'),
    (7, 'QA', 'Source water agency audit schedule', 'SH/26/007', 'Yearly & 2-yearly'),
    (8, 'QA', 'Schedule for water analysis by outside party for source water', 'SH/26/008', 'Yearly'),
    (9, 'QA', 'Schedule for audit trail review of indirect impact system', 'SH/26/009', 'Monthly'),
    (10, 'Stores & Production', 'Schedule for Temperature distribution study schedule', 'SH/26/0010', '3 years once'),
    (11, 'QA', 'Annual schedule for review of user management policy', 'SH/26/0011', 'half yearly'),
    (12, 'QA', 'Schedule for periodic qualification of visual inspection', 'SH/26/0012', '2 years once'),
    (13, 'IT', 'Backup and restoration validation schedule', 'SH/26/0013', '2 years once'),
    (14, 'QA', 'Admin planner for schedule tracking - year 2026', 'SH/26/0014', 'Monthly'),
    (15, 'QA', 'Stores planner for schedule tracking - year 2026', 'SH/26/0015', 'Monthly'),
    (16, 'QA', 'IT planner for schedule tracking - year 2026', 'SH/26/0016', 'Monthly'),
    (17, 'QA', 'Production planner for schedule tracking - year 2026', 'SH/26/0017', 'Monthly'),
    (18, 'QA', 'Engineering planner for schedule tracking - year 2026', 'SH/26/0018', 'Monthly'),
    (19, 'QA', 'QA planner for schedule tracking - year 2026', 'SH/26/0019', 'Monthly'),
    (20, 'QA', 'Annual training schedule for Admin', 'SH/26/0020', 'Monthly'),
    (21, 'QA', 'Annual training schedule for Stores', 'SH/26/0021', 'Monthly'),
    (22, 'QA', 'Annual training schedule for API I', 'SH/26/0022', 'Monthly'),
    (23, 'QA', 'Annual training schedule for API II', 'SH/26/0023', 'Monthly'),
    (24, 'QA', 'Annual training schedule for ATS', 'SH/26/0024', 'Monthly'),
    (25, 'QA', 'Annual training schedule for TT', 'SH/26/0025', 'Monthly'),
    (26, 'QA', 'Annual training schedule for PPIC', 'SH/26/0026', 'Monthly'),
    (27, 'QA', 'Annual training schedule for ME', 'SH/26/0027', 'Monthly'),
    (28, 'QA', 'Annual training schedule for QA', 'SH/26/0028', 'Monthly'),
    (29, 'QA', 'Annual training schedule for QA Contract', 'SH/26/0029', 'Monthly'),
    (30, 'QA', 'Annual training schedule for Engineering', 'SH/26/0030', 'Monthly'),
    (31, 'QA', 'Annual training schedule for Engineering contract', 'SH/26/0031', 'Monthly'),
    (32, 'QA', 'Annual training schedule for EHS', 'SH/26/0032', 'Monthly'),
    (33, 'QA', 'Annual training schedule for QC', 'SH/26/0033', 'Monthly'),
    (34, 'QA', 'Annual Training planner schedule for HR', 'SH/26/0034', 'Monthly'),
    (35, 'Engineering', 'Annual equipment review report schedule', 'SH/26/0035', 'Annually'),
    (36, 'API I', 'Visual Inspection schedule', 'SH/26/0036', 'Annually'),
    (37, 'API I', 'Equipment cleaning schedule', 'SH/26/0037', 'Annually'),
    (38, 'API I', 'Surface Finish schedule', 'SH/26/0038', 'Annually'),
    (39, 'API I', 'Periodic Seasonal study', 'SH/26/0039', 'Quarterly'),
    (40, 'API II Stream 3', 'Surface Finish schedule', 'SH/26/0040', 'Annually'),
    (41, 'QC Micro', 'Microbiology schedule for month of January-2026', 'SH/26/0041', 'Monthly'),
    (42, 'API 2', 'Fumigation schedule for API-2', 'SH/26/0042', 'half yearly'),
    (43, 'API II Stream 1', 'Surface Finish schedule for equipment Stream-1', 'SH/26/0043', 'Annually'),
    (44, 'API 2', 'Equipment visual inspection API-2', 'SH/26/0044', '2 years once'),
    (45, 'API 2', 'Equipment cleaning qualification', 'SH/26/0045', '2 years once'),
    (46, 'QA', 'Annual periodic schedule for risk assessment by QRM', 'SH/26/0046', 'Annually'),
    (47, 'QA', 'Annual training schedule for IT', 'SH/26/0047', 'Monthly'),
    (48, 'API II Stream 2', 'Surface Finish schedule for equipment Stream-2', 'SH/26/0048', 'Annually'),
    (49, 'Admin', 'Schedule for kitchen verification', 'SH/26/0049', 'Quarterly'),
    (50, 'Admin', 'Schedule for laundry verification', 'SH/26/0050', 'Annually'),
    (51, 'QA', 'Schedule for review of Cipdox audit trail', 'SH/26/0051', 'Quarterly'),
    (52, 'Admin', 'Schedule For Preparation of Trend Report for Pest Control for the Year-2026', 'SH/26/0052', 'Monthly'),
    (53, 'QC', 'Periodic Skip testing schedule for 2026', 'SH/26/0053', 'Yearly once'),
    (54, 'QA', 'Schedule for periodic review of PDE report', 'SH/26/0054', '3 years once'),
    (55, 'API II Stream V', 'Surface Finish schedule for equipment Stream-5', 'SH/26/0055', 'Annually'),
    (56, 'API II Stream IV', 'Surface Finish schedule for equipment Stream-4', 'SH/26/0056', 'Annually'),
    (57, 'QA', 'Schedule for daily backup of format and bound book excel', 'SH/26/0057', 'Daily'),
    (58, 'IT', 'Preventive maintenance schedule for network rack', 'SH/26/0058', 'half yearly'),
    (59, 'IT', 'Preventive maintenance schedule of IT system', 'SH/26/0059', 'Yearly once'),
    (60, 'Production', 'Standard weight calibration schedule', 'SH/26/0060', 'Yearly once'),
    (61, 'IT', 'Tape verification schedule and log', 'SH/26/0061', 'Yearly once'),
    (62, 'Engineering', 'HMI healthiness verification schedule', 'SH/26/0062', 'Monthly'),
    (63, 'QC', 'Annual Training schedule (Contract Person) QC', 'SH/26/0063', 'Monthly'),
    (64, 'QC', 'Annual Training schedule Microbiology', 'SH/26/0064', 'Monthly'),
    (65, 'QA', 'Schedule For Verification of Documents in Storage Areas/Rooms', 'SH/26/0065', 'Fortnightly'),
    (66, 'QC Micro', 'Microbiology schedule for year 2026 to 2031', 'SH/26/0066', 'Yearly once'),
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


# The three module groups, shown as category tiles on the landing page —
# each one drills into a category page listing every module (built or
# placeholder) that belongs to it.
CATEGORIES = [
    {'key': 'logs', 'title': 'Logs'},
    {'key': 'forms', 'title': 'Forms'},
    {'key': 'schedulers', 'title': 'Scheduler'},
]


def main_menu(request):
    active_filter = request.GET.get('filter')

    if active_filter in ('logs', 'forms', 'schedulers'):
        category = next(c for c in CATEGORIES if c['key'] == active_filter)
        items = [_resolve(m) for m in MODULES if m['group'] == active_filter]
        return render(
            request,
            'main_menu.html',
            {'greeting': _greeting(), 'category': category, 'items': items},
        )

    equipment_log = _resolve(next(m for m in MODULES if m['key'] == 'equipment-log'))
    analytics = _resolve(next(m for m in MODULES if m['key'] == 'analytics'))
    category_tiles = [
        {
            'title': c['title'],
            'group': c['key'],
            'url': f"{reverse('main_menu')}?filter={c['key']}",
            'available': True,
            'count': sum(1 for m in MODULES if m['group'] == c['key']),
        }
        for c in CATEGORIES
    ]
    return render(
        request,
        'main_menu.html',
        {'greeting': _greeting(), 'category': None, 'items': [equipment_log] + category_tiles + [analytics]},
    )


def module_placeholder(request, slug):
    module = next((m for m in MODULES if m['key'] == slug), None)
    title = module['title'] if module else slug.replace('-', ' ').title()
    if slug == 'list-of-schedules':
        groups = {label: [] for label in FREQUENCY_ORDER}
        for sr_no, department, name, schedule_number, raw_frequency in SCHEDULES:
            label = _FREQUENCY_ALIASES[raw_frequency.strip().lower()]
            groups[label].append({
                'sr_no': sr_no, 'department': department, 'name': name, 'schedule_number': schedule_number,
            })
        frequency_groups = [
            {'label': label, 'items': groups[label]} for label in FREQUENCY_ORDER if groups[label]
        ]
        return render(request, 'schedule_list.html', {'title': title, 'frequency_groups': frequency_groups})
    return render(request, 'placeholder.html', {'title': title})
