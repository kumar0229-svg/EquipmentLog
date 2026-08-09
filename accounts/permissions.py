from functools import wraps

from django.core.exceptions import PermissionDenied

from .models import Role


def role_required(*roles):
    """Server-side role gate. Admins and superusers always pass."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                raise PermissionDenied
            if user.is_admin_role or user.role in roles:
                return view(request, *args, **kwargs)
            raise PermissionDenied

        return wrapper

    return decorator


ALL_ROLES = [Role.OPERATOR, Role.ENGINEER, Role.QA, Role.SECTION_HEAD, Role.ADMIN]
