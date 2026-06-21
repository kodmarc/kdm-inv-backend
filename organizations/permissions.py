from rest_framework import permissions

class IsOrganizationHQUser(permissions.BasePermission):
    """
    Allows access only to authenticated Organization Admins and Organization Users.
    """
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
            
        # Check role and active organization link
        return (
            user.role in [user.Role.ORG_ADMIN, user.Role.ORG_USER] 
            and user.organization is not None
        )

class PolicyBasedCRUDPermission(permissions.BasePermission):
    """
    Permission class checking policy settings for Items and Companies:
    - Centralized Mode ('ORG_ADMIN'): Only HQ users (ORG_ADMIN, ORG_USER) can write. Branch users can read.
    - Decentralized Mode ('BRANCH_ADMIN'): Only branch users (BRANCH_ADMIN, USER) can write (scoped). HQ users can read.
    """
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.organization:
            return False

        if request.method in permissions.SAFE_METHODS:
            return True

        policy_attr = 'item_creation_policy' if getattr(view, 'policy_type', 'item') == 'item' else 'company_creation_policy'
        policy = getattr(user.organization, policy_attr)

        if policy == 'ORG_ADMIN':
            return user.role in ['ORG_ADMIN', 'ORG_USER']
        else:
            return user.role in ['BRANCH_ADMIN', 'USER'] and user.branch is not None

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if request.method in permissions.SAFE_METHODS:
            return True

        policy_attr = 'item_creation_policy' if getattr(view, 'policy_type', 'item') == 'item' else 'company_creation_policy'
        policy = getattr(user.organization, policy_attr)

        if policy == 'ORG_ADMIN':
            return user.role in ['ORG_ADMIN', 'ORG_USER']
        else:
            # Under decentralized mode, must match branch
            return user.role in ['BRANCH_ADMIN', 'USER'] and obj.branch == user.branch

