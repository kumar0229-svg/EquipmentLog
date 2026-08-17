from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import Role
from accounts.permissions import role_required

from masters.models import ComputerizedSystem, SiteSetting

from .forms import CloseoutForm, EntryFilterForm, LogIncidentForm, SelectIncidentForm, SelectSystemForm
from .models import IncidentStatus, SoftwareIncidentEntry

PRINT_ROWS_PER_PAGE = 25


def _filtered_entries(form):
    entries = SoftwareIncidentEntry.objects.select_related('system', 'logged_by', 'verified_by')
    if form.is_valid():
        if form.cleaned_data['system']:
            entries = entries.filter(system=form.cleaned_data['system'])
        if form.cleaned_data['date_from']:
            entries = entries.filter(logged_date__gte=form.cleaned_data['date_from'])
        if form.cleaned_data['date_to']:
            entries = entries.filter(logged_date__lte=form.cleaned_data['date_to'])
    return entries


def _filters_display(form):
    if not form.is_valid():
        return 'None'
    parts = []
    if form.cleaned_data.get('system'):
        parts.append(f"System: {form.cleaned_data['system'].name}")
    if form.cleaned_data.get('date_from'):
        parts.append(f"From: {form.cleaned_data['date_from'].strftime('%d.%m.%Y')}")
    if form.cleaned_data.get('date_to'):
        parts.append(f"To: {form.cleaned_data['date_to'].strftime('%d.%m.%Y')}")
    return ' | '.join(parts) if parts else 'None (showing all entries)'


@login_required
def entry_list(request):
    form = EntryFilterForm(request.GET or None)
    entries = _filtered_entries(form)
    return render(
        request, 'software_incident_log/entry_list.html',
        {'form': form, 'entries': entries[:500], 'query': request.GET.urlencode()},
    )


@login_required
def entry_list_print(request):
    form = EntryFilterForm(request.GET or None)
    entries = list(_filtered_entries(form)[:500])
    pages = [
        entries[i:i + PRINT_ROWS_PER_PAGE] for i in range(0, len(entries), PRINT_ROWS_PER_PAGE)
    ] or [[]]

    return render(
        request, 'software_incident_log/entry_list_print.html',
        {
            'pages': pages,
            'filters_display': _filters_display(form),
            'location': SiteSetting.get_location(),
            'generated_at': timezone.localtime(),
        },
    )


@login_required
def log_incident(request):
    action = request.POST.get('action')

    if request.method == 'POST' and action in ('preview', 'edit', 'submit'):
        form = LogIncidentForm(request.POST)

        if action == 'edit':
            return render(request, 'software_incident_log/log_form.html', {'form': form, 'preview': False})

        if form.is_valid():
            if action == 'preview':
                return render(request, 'software_incident_log/log_form.html', {'form': form, 'preview': True})

            try:
                with transaction.atomic():
                    entry = SoftwareIncidentEntry.objects.create(
                        incident_no=form.cleaned_data['incident_no'],
                        system=form.cleaned_data['system'],
                        description=form.cleaned_data['description'],
                        logged_by=request.user,
                    )
            except IntegrityError:
                # A same-instant race between two submissions of the same
                # Incident No — the form's own uniqueness check already
                # covers the common case of a stale/duplicate entry.
                form.add_error('incident_no', 'This Incident No has already been used.')
                return render(request, 'software_incident_log/log_form.html', {'form': form, 'preview': False})

            messages.success(request, f'Incident logged — {entry.incident_no}.')
            return redirect('software_incident_log')

        return render(request, 'software_incident_log/log_form.html', {'form': form, 'preview': False})

    form = LogIncidentForm()
    return render(request, 'software_incident_log/log_form.html', {'form': form, 'preview': False})


@login_required
@role_required(Role.QA)
def select_incident_to_close(request):
    """Two-step picker: choose the Computerized System first, then choose
    from that system's open incidents, before landing on the closeout form.
    """
    if not SoftwareIncidentEntry.objects.filter(status=IncidentStatus.OPEN).exists():
        messages.info(request, 'There are no open incidents to close.')
        return redirect('software_incident_log')

    if request.method == 'POST' and request.POST.get('action') == 'pick-incident':
        system = get_object_or_404(ComputerizedSystem, pk=request.POST.get('system'))
        form = SelectIncidentForm(request.POST, system=system)
        if form.is_valid():
            return redirect('software_incident_log_closeout', pk=form.cleaned_data['incident'].pk)
        return render(
            request, 'software_incident_log/select_close.html',
            {'stage': 'incident', 'system': system, 'form': form},
        )

    if request.method == 'POST':
        system_form = SelectSystemForm(request.POST)
        if system_form.is_valid():
            system = system_form.cleaned_data['system']
            if not SoftwareIncidentEntry.objects.filter(status=IncidentStatus.OPEN, system=system).exists():
                messages.info(request, f'There are no open incidents for {system.name}.')
                return redirect('software_incident_log_select_close')
            form = SelectIncidentForm(system=system)
            return render(
                request, 'software_incident_log/select_close.html',
                {'stage': 'incident', 'system': system, 'form': form},
            )
        return render(request, 'software_incident_log/select_close.html', {'stage': 'system', 'form': system_form})

    return render(
        request, 'software_incident_log/select_close.html', {'stage': 'system', 'form': SelectSystemForm()},
    )


@login_required
@role_required(Role.QA)
def closeout(request, pk):
    entry = get_object_or_404(SoftwareIncidentEntry, pk=pk)
    if entry.status != IncidentStatus.OPEN:
        messages.error(request, 'This incident is already closed.')
        return redirect('software_incident_log')

    if request.method == 'POST':
        form = CloseoutForm(request.POST, instance=entry)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.verified_by = request.user
            entry.closeout_date = timezone.localdate()
            entry.status = IncidentStatus.CLOSED
            entry.save()
            messages.success(request, f'Incident {entry.incident_no} closed.')
            return redirect('software_incident_log')
    else:
        form = CloseoutForm(instance=entry)

    return render(request, 'software_incident_log/closeout_form.html', {'form': form, 'entry': entry})
