def nav_section(request):
    """Whether the current page is the main menu.

    Drives base.html's nav: every page except the main menu itself just
    shows a "Back to Main Menu" link — the menu's own tiles are the nav.
    """
    return {'on_main_menu': request.path_info == '/'}
