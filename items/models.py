import uuid
from django.db import models
from organizations.models import Organization
from companies.models import Company

class ItemCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name='item_categories'
    )
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Item Categories'
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'name'],
                name='unique_org_category_name'
            ),
            models.UniqueConstraint(
                fields=['organization', 'code'],
                name='unique_org_category_code'
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.code:
            count = ItemCategory.objects.filter(organization=self.organization).count()
            self.code = f"CAT-{count + 1:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.code})"


class Item(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name='items'
    )
    category = models.ForeignKey(
        ItemCategory,
        on_delete=models.PROTECT,
        related_name='items'
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name='items',
        null=True,
        blank=True
    )
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True)
    sku = models.CharField(max_length=100, blank=True, null=True)
    pack = models.IntegerField(null=True, blank=True)
    grammage = models.CharField(max_length=50, blank=True, null=True)
    purchase_rate = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    sales_rate = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    purchase_tax = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    sales_tax = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    federal_tax = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    discount_slab_qty = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    discount_slab_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    min_stock = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    max_stock = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    current_stock = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    damaged_stock = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'name'],
                name='unique_org_item_name'
            ),
            models.UniqueConstraint(
                fields=['organization', 'code'],
                name='unique_org_item_code'
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.code:
            count = Item.objects.filter(organization=self.organization).count()
            self.code = f"ITEM-{count + 1:04d}"
        if not self._state.adding:
            self.version += 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.code})"
