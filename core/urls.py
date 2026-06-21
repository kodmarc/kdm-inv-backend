from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('accounts.urls')),
    path('api/', include('organizations.urls')),
    path('api/', include('companies.urls')),
    path('api/', include('items.urls')),
    path('api/', include('registers.urls')),
]
