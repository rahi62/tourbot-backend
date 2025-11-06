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
        if view.action in ['create', 'list']:
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
        # Handle unauthenticated users
        if not request.user.is_authenticated:
            return False
        
        # Check if user has required methods (for CustomUser model)
        if not hasattr(request.user, 'is_admin'):
            return False
        
        # Admins can do anything
        if request.user.is_admin():
            return True
        
        # Agencies can view all visa requests
        if hasattr(request.user, 'is_agency') and request.user.is_agency():
            return True
        
        # For travelers, check if this is their own request
        # If obj has a user field, check ownership
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        
        # For travelers, allow view if no user field (legacy support)
        if hasattr(request.user, 'is_traveler') and request.user.is_traveler():
            return view.action in ['list', 'retrieve']  # Only allow read operations
        
        return False

