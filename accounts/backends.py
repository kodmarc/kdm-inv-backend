from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

class MultiTenantAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, org_id=None, branch_slug=None, role=None, **kwargs):
        User = get_user_model()
        if not username or not password or not org_id or not role:
            return None

        # Clean inputs
        org_id_clean = org_id.lower().strip()
        username_clean = username.strip()

        try:
            # Authenticate HQ roles (Organization Admin / User)
            if role in [User.Role.ORG_ADMIN, User.Role.ORG_USER]:
                user = User.objects.get(
                    organization__org_id=org_id_clean,
                    username=username_clean,
                    role=role
                )
            # Authenticate Branch roles (Branch Admin, User, KPO)
            else:
                if not branch_slug:
                    return None
                user = User.objects.get(
                    organization__org_id=org_id_clean,
                    branch__slug=branch_slug.strip(),
                    username=username_clean,
                    role=role
                )

            # Check password and active status
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        except User.DoesNotExist:
            return None
        return None
