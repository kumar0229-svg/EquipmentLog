import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role
from accounts.permissions import role_required
from masters.models import SiteSetting

from .forms import EntryFilterForm, IssueBMRForm
from .models import BMRIssuanceEntry

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
    return ' | '.join(parts) if parts else 'None (showing all entries)'


def _fmt_date(value):
    return value.strftime('%d.%m.%Y') if value else ''


def _fmt_time(value):
    return value.strftime('%H.%M') if value else ''


def _export_csv(entries):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="bmr_issuance_log.csv"'
    writer = csv.writer(response)
    writer.writerow(
        [
            'Batch No', 'Type of Batch', 'Process Order No', 'Product Name', 'Master Document No',
            'Production Block', 'Issued To', 'Issued By', 'Issued Date', 'Issued Time', 'Remarks',
        ]
    )
    for e in entries:
        writer.writerow(
            [
                e.batch_no, e.get_batch_type_display(), e.process_order_no, e.product.name,
                e.master_document_no, e.production_block.name,
                e.issued_to.get_full_name() or e.issued_to.username,
                e.issued_by.get_full_name() or e.issued_by.username,
                _fmt_date(e.issued_date), _fmt_time(e.issued_time), e.remarks,
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


@login_required
def entry_detail(request, pk):
    entry = get_object_or_404(
        BMRIssuanceEntry.objects.select_related('product', 'production_block', 'issued_to', 'issued_by'), pk=pk
    )
    return render(request, 'bmr_log/entry_detail.html', {'entry': entry})


@login_required
@role_required(Role.QA)
def issue_bmr(request):
    if request.method == 'POST':
        form = IssueBMRForm(request.POST)
        if form.is_valid():
            now = timezone.localtime()
            entry = form.save(commit=False)
            entry.issued_by = request.user
            entry.issued_date = now.date()
            entry.issued_time = now.time().replace(second=0, microsecond=0)
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
                messages.success(request, f'BMR issued — Batch No {entry.batch_no}.')
                return redirect('bmr_entry_detail', pk=entry.pk)
    else:
        form = IssueBMRForm()

    return render(request, 'bmr_log/issue_form.html', {'form': form})
