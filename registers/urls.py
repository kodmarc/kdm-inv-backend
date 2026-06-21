from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    OrderBookerViewSet,
    SalesmanViewSet,
    PartyViewSet,
    AccountOpeningViewSet,
    SalesInvoiceViewSet,
    PurchaseInvoiceViewSet,
    PurchaseReturnViewSet,
    DamageReturnViewSet,
    DamageReceivingViewSet
)

router = DefaultRouter()
router.register('order-bookers', OrderBookerViewSet, basename='order-booker')
router.register('salesmen', SalesmanViewSet, basename='salesman')
router.register('parties', PartyViewSet, basename='party')
router.register('accounts', AccountOpeningViewSet, basename='account')
router.register('sales-invoices', SalesInvoiceViewSet, basename='sales-invoice')
router.register('purchase-invoices', PurchaseInvoiceViewSet, basename='purchase-invoice')
router.register('purchase-returns', PurchaseReturnViewSet, basename='purchase-return')
router.register('damage-returns', DamageReturnViewSet, basename='damage-return')
router.register('damage-receivings', DamageReceivingViewSet, basename='damage-receiving')

urlpatterns = [
    path('', include(router.urls)),
]


