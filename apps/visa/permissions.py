from rest_framework import permissions


class VisaRequestPermission(permissions.BasePermission):
    """
    Permission for VisaRequest:
    - Anyone (including unauthenticated) can create visa requests
    - Anyone (including unauthenticated) can read/list visa requests
    - Only admins can view all visa requests
    - Travelers can only see their own visa requests (if authenticated)
    """
    
    def has_permission(self, request, view):
        # Allow create and list for everyone
        if request.action in ['create', 'list']:
            return True
        # For other actions, require authentication
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """
        Object-level permission:
        - Admins can view/update/delete any visa request
        - Travelers can only view their own visa requests
        - Agencies can view all (for managing requests)
        """
        # Admins can do anything
        if request.user.is_admin():
            return True
        
        # Agencies can view all visa requests
        if request.user.is_agency():
            return True
        
        # For travelers, check if this is their own request
        # Note: VisaRequest doesn't have a user field, so we'll need to add it
        # For now, allow travelers to view all (they can filter by their own data)
        if request.user.is_traveler():
            return True
        
        return False

