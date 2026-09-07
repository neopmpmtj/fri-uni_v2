from django.http import HttpResponseForbidden

from .models import User


class StaffAdminBlockMiddleware:
    """Authenticated role=staff must not use Django contrib admin."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/admin/") and getattr(request, "user", None):
            user = request.user
            if user.is_authenticated and getattr(user, "role", None) != User.Role.ADMIN:
                return HttpResponseForbidden()
        return self.get_response(request)
