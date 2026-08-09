from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Equipment


@login_required
def equipment_list(request):
    equipment = (
        Equipment.objects.filter(active=True)
        .select_related('equipment_type', 'area')
        .order_by('equipment_type__name', 'code')
    )
    return render(request, 'masters/equipment_list.html', {'equipment': equipment})
