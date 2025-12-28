from rest_framework.permissions import BasePermission
from .auth import BrandPrincipal

class IsBrandPrincipal(BasePermission):
    def has_permission(self, request, view):
        return isinstance(request.user, BrandPrincipal)
