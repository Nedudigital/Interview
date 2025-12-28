from django.contrib import admin
from django.urls import path
from licenses import views
from licenses.views import DeactivateLicenseView
from licenses.views import (
    ProvisionLicenseView, ActivateLicenseView, CheckLicenseKeyView,
    ListLicensesByEmailView, DeactivateLicenseView, LicenseLifecycleView
)


urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/v1/licenses/provision/", views.ProvisionLicenseView.as_view(), name="provision"),
    path("api/v1/licenses/activate/", views.ActivateLicenseView.as_view(), name="activate"),
    path("api/v1/licenses/check/", views.CheckLicenseKeyView.as_view(), name="check"),
    path("api/v1/internal/licenses/by-email/", views.ListLicensesByEmailView.as_view(), name="by_email"),
      path("api/v1/licenses/deactivate/", DeactivateLicenseView.as_view(), name="deactivate"),
       path("api/v1/licenses/provision/", ProvisionLicenseView.as_view(), name="provision"),
  path("api/v1/licenses/activate/", ActivateLicenseView.as_view(), name="activate"),
  path("api/v1/licenses/check/", CheckLicenseKeyView.as_view(), name="check"),
  path("api/v1/licenses/deactivate/", DeactivateLicenseView.as_view(), name="deactivate"),
  path("api/v1/licenses/lifecycle/", LicenseLifecycleView.as_view(), name="lifecycle"),
  path("api/v1/internal/licenses/by-email/", ListLicensesByEmailView.as_view(), name="by_email"),

]
