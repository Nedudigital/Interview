from django.urls import path
from .views import DeactivateLicenseView

from . import views

urlpatterns = [
    path("api/v1/licenses/provision/", ProvisionLicenseView.as_view(), name="provision"),
    path("api/v1/licenses/activate/", ActivateLicenseView.as_view(), name="activate"),
    path("api/v1/licenses/check/", CheckLicenseKeyView.as_view(), name="check"),

    # ✅ ADD THIS
    path("api/v1/licenses/deactivate/", DeactivateLicenseView.as_view(), name="deactivate"),

    path(
        "api/v1/internal/licenses/by-email/",
        ListLicensesByEmailView.as_view(),
        name="by_email",
    ),
]
