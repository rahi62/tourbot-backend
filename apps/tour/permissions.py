from rest_framework import permissions


class IsAuthenticatedOrReadOnly(permissions.BasePermission):
    """
    Custom permission to allow read-only access to unauthenticated users,
    but require authentication for create, update, and delete operations.
    """
    
    def has_permission(self, request, view):
        # Allow read-only access for GET, HEAD, OPTIONS
        if request.method in permissions.SAFE_METHODS:
            return True
        # Require authentication for write operations
        return request.user and request.user.is_authenticated


class IsAuthenticatedForWrite(permissions.BasePermission):
    """
    Permission that allows:
    - Read access for everyone (GET, HEAD, OPTIONS)
    - Write access only for authenticated users (POST, PUT, PATCH, DELETE)
    """
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated


class IsAgencyOrAdminForWrite(permissions.BasePermission):
    """
    Permission that allows:
    - Read access for everyone (GET, HEAD, OPTIONS) - including unauthenticated users
    - Write access (POST, PUT, PATCH, DELETE) only for users with role 'agency' or 'admin'
    """
    
    def has_permission(self, request, view):
        # Allow read-only access for everyone
        if request.method in permissions.SAFE_METHODS:
            return True
        # For write operations, require authentication and agency/admin role
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.can_manage_tours()
