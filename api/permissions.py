from rest_framework.permissions import BasePermission

class IsAdminUserOrPostOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method == 'POST':
            return True
        return request.user.is_staff
    