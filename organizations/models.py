import uuid
from django.db import models
from django.core.validators import RegexValidator, MinLengthValidator

class Organization(models.Model):
    class Policy(models.TextChoices):
        ORG_ADMIN = 'ORG_ADMIN', 'Centralized (Org Admin Only)'
        BRANCH_ADMIN = 'BRANCH_ADMIN', 'Decentralized (Branch Admins)'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Custom Unique Org ID (e.g. kdm101).
    org_id = models.CharField(
        max_length=50,
        unique=True,
        validators=[
            MinLengthValidator(5, message='Organization ID must be at least 5 characters long.'),
            RegexValidator(
                regex=r'^[a-zA-Z0-9]+$',
                message='Organization ID must contain only letters and numbers without special characters.'
            ),
            RegexValidator(
                regex=r'[a-zA-Z]',
                message='Organization ID must contain at least one letter.'
            ),
            RegexValidator(
                regex=r'[0-9]',
                message='Organization ID must contain at least one number.'
            ),
        ]
    )
    name = models.CharField(max_length=255)
    
    # Policy controls for data scoping
    company_creation_policy = models.CharField(
        max_length=20,
        choices=Policy.choices,
        default=Policy.ORG_ADMIN
    )
    item_creation_policy = models.CharField(
        max_length=20,
        choices=Policy.choices,
        default=Policy.ORG_ADMIN
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Enforce lowercase on org_id for case-insensitive unique matching
        self.org_id = self.org_id.lower().strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.org_id})"


class Branch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name='branches')
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Branches'
        unique_together = ('organization', 'slug')

    def __str__(self):
        return f"{self.name} - {self.organization.name}"


class BranchSequence(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='sequences')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='sequences', null=True, blank=True)
    sequence_type = models.CharField(max_length=50)  # e.g., 'SAL', 'PUR', 'ACC'
    next_val = models.IntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'sequence_type'],
                condition=models.Q(branch__isnull=True),
                name='unique_org_sequence_type'
            ),
            models.UniqueConstraint(
                fields=['branch', 'sequence_type'],
                condition=models.Q(branch__isnull=False),
                name='unique_branch_sequence_type'
            ),
        ]

    def __str__(self):
        scope = self.branch.name if self.branch else "Global"
        return f"{scope} - {self.sequence_type}: {self.next_val}"


def get_next_sequence_value(organization, branch, sequence_type):
    from django.db import transaction, IntegrityError
    
    # We must operate in a transaction block to use select_for_update
    try:
        with transaction.atomic():
            seq = BranchSequence.objects.select_for_update().get(
                organization=organization,
                branch=branch,
                sequence_type=sequence_type
            )
    except BranchSequence.DoesNotExist:
        try:
            with transaction.atomic():
                seq = BranchSequence.objects.create(
                    organization=organization,
                    branch=branch,
                    sequence_type=sequence_type,
                    next_val=1
                )
            # Re-fetch and lock the newly created row
            with transaction.atomic():
                seq = BranchSequence.objects.select_for_update().get(id=seq.id)
        except IntegrityError:
            # Concurrent creation won the race, fetch and lock it
            with transaction.atomic():
                seq = BranchSequence.objects.select_for_update().get(
                    organization=organization,
                    branch=branch,
                    sequence_type=sequence_type
                )
                
    current_val = seq.next_val
    seq.next_val += 1
    seq.save(update_fields=['next_val'])
    return current_val

