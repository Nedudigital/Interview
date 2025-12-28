# licenses/views.py

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .auth import BrandAPIKeyAuthentication
from .models import LicenseKey, License, Activation, Product
from .serializers import ProvisionLicenseSerializer, ActivateSerializer


class ProvisionLicenseView(APIView):
    """
    US1 (core): Brand provisions a license key + one or more licenses (products) under that key.
    Auth: Brand API Key.
    """
    authentication_classes = [BrandAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        brand = request.user.brand  # BrandPrincipal -> Brand

        serializer = ProvisionLicenseSerializer(
            data=request.data,
            context={"brand": brand}
        )
        serializer.is_valid(raise_exception=True)
        products = serializer.validated_data["product_codes"]  # list[Product]

        # Find or create a license key for this customer+brand.
        # Supports "single key for RankMath + addons".
        license_key, _created = LicenseKey.objects.get_or_create(
            brand=brand,
            customer_email=serializer.validated_data["customer_email"],
            defaults={"key": LicenseKey.generate_key()},
        )

        licenses_out = []
        for product in products:
            lic, created = License.objects.get_or_create(
                license_key=license_key,
                product=product,
                defaults={
                    "status": License.STATUS_VALID,
                    "expires_at": timezone.now() + timedelta(days=365),
                }
            )
            # If already exists, keep it as-is for now.
            licenses_out.append(lic)

        return Response(
            {
                "license_key": license_key.key,
                "brand": brand.name,
                "customer_email": license_key.customer_email,
                "licenses": [
                    {
                        "product": lic.product.code,
                        "status": lic.status,
                        "expires_at": lic.expires_at.isoformat(),
                    }
                    for lic in licenses_out
                ],
            },
            status=status.HTTP_201_CREATED
        )


class ActivateLicenseView(APIView):
    """
    US3 (core): End-user product activates a license key for an instance_id.
    No auth for this exercise (call out rate limiting + abuse prevention in docs).
    """
    def post(self, request):
        s = ActivateSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        lk = LicenseKey.objects.filter(key=s.validated_data["license_key"]).first()
        if not lk:
            return Response({"detail": "License key not found"}, status=404)

        # Activate all ACTIVE licenses under that key (simple + matches “key unlocks multiple products”)
        active_licenses = [
            lic for lic in lk.licenses.select_related("product").all()
            if lic.is_active()
        ]
        if not active_licenses:
            return Response({"detail": "No active licenses on this key"}, status=403)

        instance_id = s.validated_data["instance_id"]
        activations = []
        for lic in active_licenses:
            act, _created = Activation.objects.get_or_create(
                license=lic,
                instance_id=instance_id,
                defaults={"revoked_at": None},
            )
            # If it existed but was revoked previously, un-revoke it.
            if act.revoked_at is not None:
                act.revoked_at = None
                act.save(update_fields=["revoked_at"])

            activations.append({"product": lic.product.code, "instance_id": instance_id})

        return Response(
            {
                "license_key": lk.key,
                "customer_email": lk.customer_email,
                "activated": activations,
            },
            status=200
        )


class DeactivateLicenseView(APIView):
    """
    US5 (optional): End-user product/customer can deactivate an activation for a product+instance_id.
    No auth for this exercise.
    """
    def post(self, request):
        license_key = request.data.get("license_key")
        product_code = request.data.get("product_code")
        instance_id = request.data.get("instance_id")

        if not license_key or not product_code or not instance_id:
            return Response(
                {"detail": "license_key, product_code and instance_id are required"},
                status=400
            )

        lk = LicenseKey.objects.filter(key=license_key).first()
        if not lk:
            return Response({"detail": "License key not found"}, status=404)

        lic = (
            License.objects
            .select_related("product", "license_key")
            .filter(license_key=lk, product__code=product_code)
            .first()
        )
        if not lic:
            return Response({"detail": "License not found for product"}, status=404)

        act = Activation.objects.filter(
            license=lic,
            instance_id=instance_id,
            revoked_at__isnull=True
        ).first()

        if not act:
            # idempotent deactivation: returning 200 is fine
            return Response(
                {
                    "license_key": lk.key,
                    "product": product_code,
                    "instance_id": instance_id,
                    "deactivated": False,
                    "detail": "No active activation found"
                },
                status=200
            )

        act.revoked_at = timezone.now()
        act.save(update_fields=["revoked_at"])

        return Response(
            {
                "license_key": lk.key,
                "product": product_code,
                "instance_id": instance_id,
                "deactivated": True,
                "revoked_at": act.revoked_at.isoformat(),
            },
            status=200
        )


class CheckLicenseKeyView(APIView):
    """
    US4 (core): Check what a license key unlocks + statuses + expiry + activations.
    """
    def get(self, request):
        key = request.query_params.get("license_key")
        if not key:
            return Response({"detail": "license_key query param is required"}, status=400)

        lk = LicenseKey.objects.filter(key=key).first()
        if not lk:
            return Response({"detail": "License key not found"}, status=404)

        licenses = lk.licenses.select_related("product", "product__brand").all()

        licenses_out = []
        for lic in licenses:
            active_instances = list(
                Activation.objects.filter(
                    license=lic,
                    revoked_at__isnull=True
                ).values_list("instance_id", flat=True)
            )

            licenses_out.append(
                {
                    "product": lic.product.code,
                    "status": lic.status,
                    "expires_at": lic.expires_at.isoformat(),
                    "is_active": lic.is_active(),
                    # NEW: what the product actually cares about
                    "is_activated": len(active_instances) > 0,
                    "active_instances": active_instances,
                }
            )

        return Response(
            {
                "license_key": lk.key,
                "brand": lk.brand.name,
                "customer_email": lk.customer_email,
                "licenses": licenses_out,
            }
        )


class ListLicensesByEmailView(APIView):
    """
    US6 (core): Brand-only internal list across all brands by email.
    In prod: internal service token / admin auth + audit logging.
    For the exercise: protect with Brand API key + IsAuthenticated.
    """
    authentication_classes = [BrandAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        email = request.query_params.get("email")
        if not email:
            return Response({"detail": "email query param is required"}, status=400)

        keys = (
            LicenseKey.objects
            .filter(customer_email=email)
            .select_related("brand")
            .prefetch_related("licenses__product")
        )

        out = []
        for lk in keys:
            out.append({
                "brand": lk.brand.name,
                "license_key": lk.key,
                "licenses": [
                    {
                        "product": lic.product.code,
                        "status": lic.status,
                        "expires_at": lic.expires_at.isoformat(),
                    }
                    for lic in lk.licenses.all()
                ]
            })

        return Response({"email": email, "results": out})


class LicenseLifecycleView(APIView):
    """
    US2 (optional): Brand can renew/suspend/resume/cancel a license.
    Auth: Brand API Key.
    """
    authentication_classes = [BrandAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        """
        Body:
          {
            "license_key": "lk_...",
            "product_code": "rankmath",
            "action": "suspend" | "resume" | "cancel" | "renew",
            "extend_days": 365   # only for renew (optional; default 365)
          }
        """
        brand = request.user.brand

        license_key = request.data.get("license_key")
        product_code = request.data.get("product_code")
        action = request.data.get("action")
        extend_days = request.data.get("extend_days")

        if not license_key or not product_code or not action:
            return Response(
                {"detail": "license_key, product_code and action are required"},
                status=400
            )

        lk = LicenseKey.objects.filter(key=license_key, brand=brand).first()
        if not lk:
            return Response({"detail": "License key not found for this brand"}, status=404)

        lic = License.objects.filter(license_key=lk, product__code=product_code).first()
        if not lic:
            return Response({"detail": "License not found for product"}, status=404)

        action = str(action).lower().strip()

        if action == "suspend":
            lic.status = License.STATUS_SUSPENDED
            lic.save(update_fields=["status"])
        elif action == "resume":
            # only resume if it wasn't cancelled
            if lic.status != License.STATUS_CANCELLED:
                lic.status = License.STATUS_VALID
                lic.save(update_fields=["status"])
        elif action == "cancel":
            lic.status = License.STATUS_CANCELLED
            lic.save(update_fields=["status"])
        elif action == "renew":
            try:
                days = int(extend_days) if extend_days is not None else 365
            except ValueError:
                return Response({"detail": "extend_days must be an integer"}, status=400)

            # if expired, renew from now; else extend from current expiry
            base = lic.expires_at if lic.expires_at and lic.expires_at > timezone.now() else timezone.now()
            lic.expires_at = base + timedelta(days=days)
            lic.status = License.STATUS_VALID
            lic.save(update_fields=["expires_at", "status"])
        else:
            return Response({"detail": "Unknown action"}, status=400)

        return Response(
            {
                "license_key": lk.key,
                "brand": brand.name,
                "product": lic.product.code,
                "status": lic.status,
                "expires_at": lic.expires_at.isoformat() if lic.expires_at else None,
            },
            status=200
        )
