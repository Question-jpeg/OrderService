from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdminUserOrPostOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method == 'POST':
            return True
        return request.user.is_staff
    
class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method not in SAFE_METHODS:
            return request.user == obj.user
        return True