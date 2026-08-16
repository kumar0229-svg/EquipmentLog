from .expiry import expire_stale_equipment_states


class ExpireCleaningValidityMiddleware:
    """Sweeps equipment out of a lapsed cleaned status once per authenticated
    request — see activitylog.expiry for why this exists instead of a
    scheduled task, and `expire_equipment_states` for the alternative of
    running it on a real schedule.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            expire_stale_equipment_states()
        return self.get_response(request)
