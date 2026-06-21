from django.contrib.auth.models import AbstractUser
from django.db import models
from organizations.models import Organization, Branch

class User(AbstractUser):
    class Role(models.TextChoices):
        ORG_ADMIN = 'ORG_ADMIN', 'Organization Admin'
        ORG_USER = 'ORG_USER', 'Organization User'
        BRANCH_ADMIN = 'BRANCH_ADMIN', 'Branch Admin'
        USER = 'USER', 'Branch User'
        KPO = 'KPO', 'KPO (Seller)'

    # Override username to disable global uniqueness index
    username = models.CharField(
        max_length=150,
        unique=False,
        help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.',
        validators=[AbstractUser.username_validator],
        error_messages={
            'unique': 'A user with that username already exists.',
        },
    )

    # Linkages
    organization = models.ForeignKey(
        Organization, 
        on_delete=models.PROTECT, 
        related_name='users',
        null=True,  # Nullable for platform superadmins if needed
        blank=True
    )
    branch = models.ForeignKey(
        Branch, 
        on_delete=models.PROTECT, 
        related_name='users',
        null=True,  # Nullable for ORG_ADMIN/ORG_USER
        blank=True
    )
    
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.KPO
    )

    class Meta:
        constraints = [
            # Username must be unique within an Organization for HQ roles (Org Admin, Org User)
            models.UniqueConstraint(
                fields=['organization', 'username'],
                condition=models.Q(role__in=['ORG_ADMIN', 'ORG_USER']),
                name='unique_org_username'
            ),
            # Username must be unique within a Branch for Branch roles (Branch Admin, Branch User, KPO)
            models.UniqueConstraint(
                fields=['branch', 'username'],
                condition=models.Q(role__in=['BRANCH_ADMIN', 'USER', 'KPO']),
                name='unique_branch_username'
            ),
        ]

    def __str__(self):
        branch_info = f" | {self.branch.name}" if self.branch else ""
        return f"{self.username} ({self.get_role_display()}{branch_info})"
