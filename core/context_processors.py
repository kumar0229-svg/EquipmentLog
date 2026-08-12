EQUIPMENT_LOG_PREFIX = '/equipment-log/'


def nav_section(request):
    """Whether the current page belongs to the Equipment Log module.

    Drives base.html's nav: inside Equipment Log, the other top-level
    modules hide behind a "Back to Main Menu" link instead of staying
    listed alongside Equipment Log's own sub-pages.
    """
    return {'in_equipment_log': request.path_info.startswith(EQUIPMENT_LOG_PREFIX)}
