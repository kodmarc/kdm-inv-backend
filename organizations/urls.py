from django.urls import path
from .views import BranchListCreateView, PublicBranchListView, OrganizationSettingsView

urlpatterns = [
    path('org-admin/branches/', BranchListCreateView.as_view(), name='branch_list_create'),
    path('auth/public-branches/', PublicBranchListView.as_view(), name='public_branch_list'),
    path('org-admin/settings/', OrganizationSettingsView.as_view(), name='org_settings'),
]
