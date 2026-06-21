import uuid
from django.db import models
from organizations.models import Organization, Branch

class Company(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, 
        on_delete=models.PROTECT, 
        related_name='companies'
    )
    branch = models.ForeignKey(
        Branch, 
        on_delete=models.PROTECT, 
        related_name='companies', 
        null=True, 
        blank=True
    )
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True)
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Companies'
        constraints = [
            # Name must be unique within an organization if globally scoped (branch is null)
            models.UniqueConstraint(
                fields=['organization', 'name'],
                condition=models.Q(branch__isnull=True),
                name='unique_org_company_name'
            ),
            # Name must be unique within a branch if locally scoped
            models.UniqueConstraint(
                fields=['branch', 'name'],
                condition=models.Q(branch__isnull=False),
                name='unique_branch_company_name'
            ),
            # Code must be unique within an organization if globally scoped
            models.UniqueConstraint(
                fields=['organization', 'code'],
                condition=models.Q(branch__isnull=True),
                name='unique_org_company_code'
            ),
            # Code must be unique within a branch if locally scoped
            models.UniqueConstraint(
                fields=['branch', 'code'],
                condition=models.Q(branch__isnull=False),
                name='unique_branch_company_code'
            ),
        ]

    def save(self, *args, **kwargs):
        # Auto-generate sequentially scoped code if left blank (e.g. COMP-0001)
        if not self.code:
            prefix = "COMP"
            if self.branch:
                count = Company.objects.filter(branch=self.branch).count()
            else:
                count = Company.objects.filter(organization=self.organization, branch__isnull=True).count()
            self.code = f"{prefix}-{count + 1:04d}"
        if not self._state.adding:
            self.version += 1
        super().save(*args, **kwargs)

    def __str__(self):
        branch_info = f" | {self.branch.name}" if self.branch else ""
        return f"{self.name} ({self.code}{branch_info})"
