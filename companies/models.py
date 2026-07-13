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
    # Companies are assigned to one or more branches via this M2M.
    # Branch users only see companies that include their branch here.
    branches = models.ManyToManyField(
        Branch,
        related_name='companies',
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
            models.UniqueConstraint(
                fields=['organization', 'name'],
                name='unique_org_company_name'
            ),
            models.UniqueConstraint(
                fields=['organization', 'code'],
                name='unique_org_company_code'
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.code:
            count = Company.objects.filter(organization=self.organization).count()
            self.code = f"COMP-{count + 1:04d}"
        if not self._state.adding:
            self.version += 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.code})"
