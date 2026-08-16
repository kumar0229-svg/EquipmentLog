import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.db.models import Max
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role
from accounts.permissions import role_required
from activitylog.models import ActivityLogEntry, EntryStatus
from masters.models import SiteSetting

from .forms import EntryFilterForm, PrepareBMRForm, TokenForm
from .models import BMRIssuanceEntry, BMRStatus, generate_token

PENDING_SUBMISSION_OVERDUE_DAYS = 2

PRINT_ROWS_PER_PAGE = 25


def _filtered_entries(form):
    entries = BMRIssuanceEntry.objects.select_related('product', 'production_block', 'issued_to', 'issued_by')
    if form.is_valid():
        if form.cleaned_data['batch_type']:
            entries = entries.filter(batch_type=form.cleaned_data['batch_type'])
        if form.cleaned_data['product']:
            entries = entries.filter(product=form.cleaned_data['product'])
        if form.cleaned_data['date_from']:
            entries = entries.filter(issued_date__gte=form.cleaned_data['date_from'])
        if form.cleaned_data['date_to']:
            entries = entries.filter(issued_date__lte=form.cleaned_data['date_to'])
        if form.cleaned_data['open_only']:
            entries = entries.exclude(status=BMRStatus.CLOSED)
    return entries


def _filters_display(form):
    """Human-readable summary of the applied filters, for the print header.

    Type of Batch is shown separately in the print header (it's mandatory for
    a print run), so it's left out of this summary to avoid repeating it.
    """
    if not form.is_valid():
        return 'None'
    parts = []
    if form.cleaned_data.get('product'):
        parts.append(f"Product: {form.cleaned_data['product'].name}")
    if form.cleaned_data.get('date_from'):
        parts.append(f"From: {_fmt_date(form.cleaned_data['date_from'])}")
    if form.cleaned_data.get('date_to'):
        parts.append(f"To: {_fmt_date(form.cleaned_data['date_to'])}")
    if form.cleaned_data.get('open_only'):
        parts.append('Open entries only')
    return ' | '.join(parts) if parts else 'None (showing all entries)'


def _fmt_date(value):
    return value.strftime('%d.%m.%Y') if value else ''


def _fmt_time(value):
    return value.strftime('%H.%M') if value else ''


def _fmt_datetime(value):
    if not value:
        return ''
    local = timezone.localtime(value)
    return f'{local.strftime("%d.%m.%Y")} {local.strftime("%H.%M")}'


def _display_name(user):
    return (user.get_full_name() or user.username) if user else ''


def _export_csv(entries):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="bmr_issuance_log.csv"'
    writer = csv.writer(response)
    writer.writerow(
        [
            'Batch No', 'Type of Batch', 'Process Order No', 'Product Name', 'Master Document No',
            'Production Block', 'Issued To', 'Status',
            'Prepared By', 'Received By', 'Received At', 'Issued By', 'Issued',
            'Returned By', 'Returned At', 'Verified By', 'Verified At',
            'Received Back By', 'Received Back At', 'Remarks',
        ]
    )
    for e in entries:
        writer.writerow(
            [
                e.batch_no, e.get_batch_type_display(), e.process_order_no, e.product.name,
                e.master_document_no, e.production_block.name,
                _display_name(e.issued_to), e.get_status_display(),
                _display_name(e.prepared_by), _display_name(e.received_by), _fmt_datetime(e.received_at),
                _display_name(e.issued_by), f'{_fmt_date(e.issued_date)} {_fmt_time(e.issued_time)}'.strip(),
                _display_name(e.returned_by), _fmt_datetime(e.returned_at),
                _display_name(e.verified_by), _fmt_datetime(e.verified_at),
                _display_name(e.received_back_by), _fmt_datetime(e.received_back_at),
                e.remarks,
            ]
        )
    return response


@login_required
def entry_list(request):
    form = EntryFilterForm(request.GET or None)
    entries = _filtered_entries(form)

    if request.GET.get('export') == 'csv':
        return _export_csv(entries)

    return render(
        request,
        'bmr_log/entry_list.html',
        {'form': form, 'entries': entries[:500], 'query': request.GET.urlencode()},
    )


@login_required
def entry_list_print(request):
    form = EntryFilterForm(request.GET or None)
    batch_type = form.cleaned_data.get('batch_type') if form.is_valid() else None

    # A print run is always scoped to one batch type — otherwise rows for
    # different types could land on the same page.
    if not batch_type:
        messages.error(request, 'Select a batch type before printing the BMR issuance log.')
        return redirect(f"{reverse('bmr_log')}?{request.GET.urlencode()}")

    entries = list(_filtered_entries(form)[:500])
    pages = [
        entries[i:i + PRINT_ROWS_PER_PAGE] for i in range(0, len(entries), PRINT_ROWS_PER_PAGE)
    ] or [[]]

    return render(
        request,
        'bmr_log/entry_list_print.html',
        {
            'pages': pages,
            'batch_type_label': dict(form.fields['batch_type'].choices)[batch_type],
            'filters_display': _filters_display(form),
            'location': SiteSetting.get_location(),
            'generated_at': timezone.localtime(),
        },
    )


def _execution_pending_since(entry):
    """When this ISSUED entry's execution finished, or None if it hasn't yet.

    "Finished" means every equipment mapped to the product (masters.
    ProductEquipment) has a COMPLETED Process activitylog entry for this
    batch and none still open. A product with no mapped equipment at all has
    nothing to wait on, so it counts as finished the moment it's Issued.
    """
    mapped_equipment_ids = list(entry.product.equipment_links.values_list('equipment_id', flat=True))
    if not mapped_equipment_ids:
        return entry.issued_date

    process_entries = ActivityLogEntry.objects.filter(
        equipment_id__in=mapped_equipment_ids, product=entry.product,
        batch_no=entry.batch_no, usage_type__name='Process',
    )
    if process_entries.filter(status=EntryStatus.IN_PROGRESS).exists():
        return None

    completed = process_entries.filter(status=EntryStatus.COMPLETED)
    completed_equipment_ids = set(completed.values_list('equipment_id', flat=True))
    if not set(mapped_equipment_ids) <= completed_equipment_ids:
        return None

    return completed.aggregate(Max('end_date'))['end_date__max']


@login_required
def pending_submission(request):
    today = timezone.localdate()
    rows = []
    for entry in BMRIssuanceEntry.objects.filter(status=BMRStatus.ISSUED).select_related('product'):
        pending_since = _execution_pending_since(entry)
        if pending_since is None:
            continue
        days_pending = (today - pending_since).days
        rows.append({'entry': entry, 'days_pending': days_pending, 'overdue': days_pending > PENDING_SUBMISSION_OVERDUE_DAYS})
    rows.sort(key=lambda row: row['days_pending'], reverse=True)
    return render(request, 'bmr_log/pending_submission.html', {'rows': rows})


@login_required
def entry_detail(request, pk):
    entry = get_object_or_404(
        BMRIssuanceEntry.objects.select_related(
            'product', 'production_block', 'issued_to', 'prepared_by', 'issued_by',
            'received_by', 'returned_by', 'verified_by', 'received_back_by',
        ),
        pk=pk,
    )

    user = request.user
    is_receiver = user.id == entry.issued_to_id or user.is_admin_role
    is_qa = user.is_qa or user.is_admin_role

    show_receive_token = entry.status == BMRStatus.PREPARED and is_receiver
    show_return_token = entry.status == BMRStatus.VERIFIED and is_qa

    context = {
        'entry': entry,
        'can_verify_receive': entry.status == BMRStatus.PREPARED and is_receiver,
        'can_mark_issued': entry.status == BMRStatus.RECEIVED and is_qa,
        'can_mark_returned': entry.status == BMRStatus.ISSUED and is_receiver,
        'can_verify_return': entry.status == BMRStatus.RETURNED and is_qa,
        'can_receive_back': entry.status == BMRStatus.VERIFIED and is_qa,
        'receive_token': entry.receive_token if show_receive_token else None,
        'return_token': entry.return_token if show_return_token else None,
        'receive_form': TokenForm() if show_receive_token else None,
        'receive_back_form': TokenForm() if show_return_token else None,
    }
    return render(request, 'bmr_log/entry_detail.html', context)


@login_required
@role_required(Role.QA)
def prepare_bmr(request):
    if request.method == 'POST':
        form = PrepareBMRForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.prepared_by = request.user
            try:
                with transaction.atomic():
                    entry.save()
            except IntegrityError as exc:
                # The form's uniqueness check already covers the common case —
                # this only catches a same-instant race between two submissions
                # of the same Batch No / Process Order No. The DB error message
                # names the failed constraint, which includes the column name.
                if 'process_order_no' in str(exc):
                    form.add_error('process_order_no', 'This Process Order No has already been issued.')
                else:
                    form.add_error('batch_no', 'This Batch No has already been issued.')
            else:
                messages.success(request, f'BMR prepared — Batch No {entry.batch_no}.')
                return redirect('bmr_entry_detail', pk=entry.pk)
    else:
        form = PrepareBMRForm()

    return render(request, 'bmr_log/prepare_form.html', {'form': form})


def _require_receiver(request, entry):
    if not (request.user.id == entry.issued_to_id or request.user.is_admin_role):
        raise PermissionDenied


@login_required
def verify_receive_bmr(request, pk):
    entry = get_object_or_404(BMRIssuanceEntry, pk=pk)
    _require_receiver(request, entry)

    if entry.status != BMRStatus.PREPARED:
        messages.error(request, 'This BMR is not awaiting receipt.')
        return redirect('bmr_entry_detail', pk=entry.pk)

    if request.method == 'POST':
        form = TokenForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['token'] != entry.receive_token:
                form.add_error('token', 'Incorrect token.')
            else:
                with transaction.atomic():
                    entry.received_by = request.user
                    entry.received_at = timezone.localtime()
                    entry.status = BMRStatus.RECEIVED
                    entry.save(update_fields=['received_by', 'received_at', 'status'])
                messages.success(request, 'BMR receipt confirmed.')
                return redirect('bmr_entry_detail', pk=entry.pk)
        messages.error(request, 'Incorrect token.')
    return redirect('bmr_entry_detail', pk=entry.pk)


@login_required
@role_required(Role.QA)
def mark_issued(request, pk):
    entry = get_object_or_404(BMRIssuanceEntry, pk=pk)
    if entry.status != BMRStatus.RECEIVED:
        messages.error(request, 'This BMR is not awaiting the Issued confirmation.')
        return redirect('bmr_entry_detail', pk=entry.pk)

    if request.method == 'POST':
        now = timezone.localtime()
        entry.issued_by = request.user
        entry.issued_date = now.date()
        entry.issued_time = now.time().replace(second=0, microsecond=0)
        entry.status = BMRStatus.ISSUED
        entry.save(update_fields=['issued_by', 'issued_date', 'issued_time', 'status'])
        messages.success(request, 'BMR marked as Issued.')
    return redirect('bmr_entry_detail', pk=entry.pk)


@login_required
def mark_returned(request, pk):
    entry = get_object_or_404(BMRIssuanceEntry, pk=pk)
    _require_receiver(request, entry)

    if entry.status != BMRStatus.ISSUED:
        messages.error(request, 'This BMR is not awaiting return.')
        return redirect('bmr_entry_detail', pk=entry.pk)

    if request.method == 'POST':
        entry.returned_by = request.user
        entry.returned_at = timezone.localtime()
        entry.return_token = generate_token()
        entry.status = BMRStatus.RETURNED
        entry.save(update_fields=['returned_by', 'returned_at', 'return_token', 'status'])
        messages.success(request, 'BMR marked as Returned.')
    return redirect('bmr_entry_detail', pk=entry.pk)


@login_required
@role_required(Role.QA)
def verify_return(request, pk):
    entry = get_object_or_404(BMRIssuanceEntry, pk=pk)
    if entry.status != BMRStatus.RETURNED:
        messages.error(request, 'This BMR is not awaiting return verification.')
        return redirect('bmr_entry_detail', pk=entry.pk)

    if request.method == 'POST':
        entry.verified_by = request.user
        entry.verified_at = timezone.localtime()
        entry.status = BMRStatus.VERIFIED
        entry.save(update_fields=['verified_by', 'verified_at', 'status'])
        messages.success(request, 'BMR return verified.')
    return redirect('bmr_entry_detail', pk=entry.pk)


@login_required
@role_required(Role.QA)
def receive_back(request, pk):
    entry = get_object_or_404(BMRIssuanceEntry, pk=pk)
    if entry.status != BMRStatus.VERIFIED:
        messages.error(request, 'This BMR is not awaiting receipt back by QA.')
        return redirect('bmr_entry_detail', pk=entry.pk)

    if request.method == 'POST':
        form = TokenForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['token'] != entry.return_token:
                form.add_error('token', 'Incorrect token.')
            else:
                with transaction.atomic():
                    entry.received_back_by = request.user
                    entry.received_back_at = timezone.localtime()
                    entry.status = BMRStatus.CLOSED
                    entry.save(update_fields=['received_back_by', 'received_back_at', 'status'])
                messages.success(request, 'BMR received back by QA — log closed.')
                return redirect('bmr_entry_detail', pk=entry.pk)
        messages.error(request, 'Incorrect token.')
    return redirect('bmr_entry_detail', pk=entry.pk)
