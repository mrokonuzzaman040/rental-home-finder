"""Role-gated view decorator, mirrors django.contrib.auth.decorators.login_required."""

from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from . import roles


def role_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped(request, *args, **kwargs):
            if request.user.is_staff or roles.role_of(request.user) in allowed_roles:
                return view_func(request, *args, **kwargs)
            messages.error(
                request, "Your account type doesn't have access to that section."
            )
            return redirect("dashboard")

        return wrapped

    return decorator
