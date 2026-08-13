import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role
from accounts.permissions import role_required
from masters.models import Area, AreaType, Equipment, SiteSetting

from . import rules
from .forms import EntryFilterForm, StartActivityForm, equipment_context_map, usage_type_field_map
from .models import ActivityLogEntry, EntryStatus

PRINT_ROWS_PER_PAGE = 25


def _server_date_and_time():
    """Current IST date/time, truncated to the minute — seconds aren't logged."""
    now = timezone.localtime()
    return now.date(), now.time().replace(second=0, microsecond=0)


@login_required
def dashboard(request, heading='Dashboard'):
    streams = Area.objects.filter(area_type=AreaType.STREAM, active=True).select_related('parent')

    # Section heads are locked to their own section's stream — no picker, no
    # cross-section visibility.
    locked_stream = None
    if request.user.is_section_head and request.user.section:
        locked_stream = streams.filter(name=request.user.section).first()

    if locked_stream:
        selected_stream = locked_stream
    else:
        stream_id = request.GET.get('stream')
        if stream_id and stream_id.isdigit():
            selected_stream = streams.filter(pk=stream_id).first()
            # Picking a stream here also makes it the default the Dashboard
            # opens to next time, so the user doesn't have to reselect it.
            if selected_stream and request.user.default_stream_id != selected_stream.id:
                request.user.default_stream = selected_stream
                request.user.save(update_fields=['default_stream'])
        else:
            selected_stream = streams.filter(pk=request.user.default_stream_id).first()

    rows = []
    if selected_stream:
        equipment = list(
            Equipment.objects.filter(active=True, area_id__in=selected_stream.descendant_ids())
            .select_related('equipment_type', 'area')
        )
        open_entries = {
            e.equipment_id: e
            for e in ActivityLogEntry.objects.filter(
                equipment__in=equipment, end_date__isnull=True
            ).select_related('product', 'usage_type')
        }
        for item in equipment:
            open_entry = open_entries.get(item.id)
            action_url = (
                reverse('stop_activity', args=[open_entry.pk])
                if open_entry
                else f"{reverse('start_activity')}?equipment={item.pk}"
            )
            rows.append(
                {
                    'equipment': item,
                    'open_entry': open_entry,
                    'action_url': action_url,
                    # Only meaningful for a Process activity — other usage types
                    # don't carry a product.
                    'product': open_entry.product
                    if open_entry and open_entry.usage_type.name == 'Process'
                    else None,
                }
            )

    return render(
        request,
        'activitylog/dashboard.html',
        {
            'heading': heading,
            'rows': rows,
            'streams': sorted(streams, key=lambda s: s.full_path),
            'selected_stream': selected_stream,
            'stream_locked': bool(locked_stream),
        },
    )


def _filtered_entries(form):
    entries = ActivityLogEntry.objects.select_related(
        'equipment', 'product', 'usage_type', 'start_by', 'end_by'
    )
    if form.is_valid():
        if form.cleaned_data['equipment']:
            entries = entries.filter(equipment=form.cleaned_data['equipment'])
        if form.cleaned_data['product']:
            entries = entries.filter(product=form.cleaned_data['product'])
        if form.cleaned_data['status']:
            entries = entries.filter(status=form.cleaned_data['status'])
        if form.cleaned_data['date_from']:
            entries = entries.filter(start_date__gte=form.cleaned_data['date_from'])
        if form.cleaned_data['date_to']:
            entries = entries.filter(start_date__lte=form.cleaned_data['date_to'])
    return entries


def _filters_display(form):
    """Human-readable summary of the applied filters, for the print header.

    Equipment is shown separately in the print header (it's mandatory for a
    print run), so it's left out of this summary to avoid repeating it.
    """
    if not form.is_valid():
        return 'None'
    parts = []
    if form.cleaned_data.get('product'):
        parts.append(f"Product: {form.cleaned_data['product'].name}")
    if form.cleaned_data.get('status'):
        status_choices = dict(form.fields['status'].choices)
        parts.append(f"Status: {status_choices[form.cleaned_data['status']]}")
    if form.cleaned_data.get('date_from'):
        parts.append(f"From: {_fmt_date(form.cleaned_data['date_from'])}")
    if form.cleaned_data.get('date_to'):
        parts.append(f"To: {_fmt_date(form.cleaned_data['date_to'])}")
    return ' | '.join(parts) if parts else 'None (showing all entries)'


@login_required
def entry_list(request):
    form = EntryFilterForm(request.GET or None)
    entries = _filtered_entries(form)

    if request.GET.get('export') == 'csv':
        return _export_csv(entries)

    return render(
        request,
        'activitylog/entry_list.html',
        {'form': form, 'entries': entries[:500], 'query': request.GET.urlencode()},
    )


@login_required
def entry_list_print(request):
    form = EntryFilterForm(request.GET or None)
    equipment = form.cleaned_data.get('equipment') if form.is_valid() else None

    # A print run is always scoped to one equipment — otherwise rows for
    # different equipment could land on the same page.
    if not equipment:
        messages.error(request, 'Select an equipment before printing the activity log.')
        return redirect(f"{reverse('entry_list')}?{request.GET.urlencode()}")

    entries = list(_filtered_entries(form)[:500])
    pages = [
        entries[i:i + PRINT_ROWS_PER_PAGE] for i in range(0, len(entries), PRINT_ROWS_PER_PAGE)
    ] or [[]]

    return render(
        request,
        'activitylog/entry_list_print.html',
        {
            'pages': pages,
            'equipment': equipment,
            'filters_display': _filters_display(form),
            'location': SiteSetting.get_location(),
            'generated_at': timezone.localtime(),
        },
    )


def _fmt_date(value):
    return value.strftime('%d.%m.%Y') if value else ''


def _fmt_time(value):
    return value.strftime('%H.%M') if value else ''


def _export_csv(entries):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="activity_log.csv"'
    writer = csv.writer(response)
    writer.writerow(
        [
            'Equipment', 'Area', 'Usage Type', 'Product', 'Batch No', 'Process Sub Activity',
            'Cleaning SOP No', 'Type of Cleaning', 'Adhered Material Removed Within 24 Hours',
            'Maintenance SOP No', 'Maintenance Type',
            'Frequency', 'PM Process Order No', 'Qualification Protocol No', 'SAP Document No',
            'Start Date', 'Start Time', 'Started By', 'End Date', 'End Time', 'Ended By',
            'Duration', 'Status', 'Remarks',
        ]
    )
    for e in entries:
        writer.writerow(
            [
                e.equipment.code, e.area_snapshot, e.usage_type.name, e.product or '', e.batch_no,
                e.get_process_sub_type_display() if e.process_sub_type else '',
                e.cleaning_sop_no, e.get_cleaning_type_display() if e.cleaning_type else '',
                e.get_adhered_material_removed_display() if e.adhered_material_removed else '',
                e.equipment_maintenance_sop_no,
                e.get_maintenance_type_display() if e.maintenance_type else '',
                e.get_maintenance_frequency_display() if e.maintenance_frequency else '',
                e.pm_process_order_no, e.qualification_protocol_no, e.sap_document_no,
                _fmt_date(e.start_date), _fmt_time(e.start_time), e.start_by.username,
                _fmt_date(e.end_date), _fmt_time(e.end_time),
                e.end_by.username if e.end_by else '', e.duration_display, e.get_status_display(),
                e.remarks,
            ]
        )
    return response


@login_required
def entry_detail(request, pk):
    entry = get_object_or_404(
        ActivityLogEntry.objects.select_related('equipment', 'product', 'usage_type'), pk=pk
    )
    return render(request, 'activitylog/entry_detail.html', {'entry': entry})


@login_required
@role_required(Role.OPERATOR, Role.ENGINEER)
def start_activity(request):
    if request.method == 'POST':
        form = StartActivityForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.start_date, entry.start_time = _server_date_and_time()
            entry.start_by = request.user
            entry.created_by = request.user
            entry.area_snapshot = entry.equipment.area.full_path
            entry.status = EntryStatus.IN_PROGRESS
            entry.save()

            entry.equipment.state = form.rule.during_state
            entry.equipment.save(update_fields=['state'])

            messages.success(request, f'Activity started on {entry.equipment.code}.')
            return redirect('dashboard')
    else:
        initial = {}
        equipment_id = request.GET.get('equipment')
        if equipment_id:
            open_entry = ActivityLogEntry.objects.filter(
                equipment_id=equipment_id, end_date__isnull=True
            ).first()
            if open_entry:
                messages.info(
                    request,
                    f'{open_entry.equipment.code} already has an activity in progress — complete it first.',
                )
                return redirect('stop_activity', pk=open_entry.pk)
            initial['equipment'] = equipment_id
        form = StartActivityForm(initial=initial)

    return render(
        request,
        'activitylog/start_activity.html',
        {
            'form': form,
            'usage_type_field_map': usage_type_field_map(),
            'equipment_context_map': equipment_context_map(),
        },
    )


@login_required
@role_required(Role.OPERATOR, Role.ENGINEER)
def stop_activity(request, pk):
    entry = get_object_or_404(ActivityLogEntry, pk=pk)
    if not entry.is_open:
        messages.error(request, 'This activity is already completed.')
        return redirect('entry_detail', pk=entry.pk)

    if request.method == 'POST':
        rule = rules.get_rule_for_entry(entry)
        if rule is None:
            messages.error(
                request,
                f'No activity rule is defined for this entry\'s sub-activity — '
                f'ask an admin or engineer to correct {entry.equipment.code} before completing it.',
            )
            return redirect('entry_detail', pk=entry.pk)

        entry.end_date, entry.end_time = _server_date_and_time()
        entry.end_by = request.user
        entry.status = EntryStatus.COMPLETED
        entry.save()

        entry.equipment.state = rule.after_state
        entry.equipment.save(update_fields=['state'])

        messages.success(request, f'Activity completed on {entry.equipment.code}.')
        return redirect('dashboard')

    return render(request, 'activitylog/stop_activity.html', {'entry': entry})
