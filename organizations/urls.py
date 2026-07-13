from django.urls import path
from .views import BranchListCreateView, BranchDetailView, PublicBranchListView

urlpatterns = [
    path('org-admin/branches/', BranchListCreateView.as_view(), name='branch_list_create'),
    path('org-admin/branches/<uuid:pk>/', BranchDetailView.as_view(), name='branch_detail'),
    path('auth/public-branches/', PublicBranchListView.as_view(), name='public_branch_list'),
]
