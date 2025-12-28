import secrets
from django.db import models
from django.utils import timezone


def generate_api_key():
    # short + recognizable prefix helps debugging
    return "br_" + secrets.token_hex(24)


class Brand(models.Model):
    name = models.CharField(max_length=255, unique=True)
    api_key = models.CharField(
        max_length=80,
        unique=True,
        default=generate_api_key,
        editable=False,
    )

    def __str__(self):
        return self.name


class Product(models.Model):
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name="products")
    code = models.CharField(max_length=64)
    name = models.CharField(max_length=255)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["brand", "code"], name="uniq_brand_product_code")
        ]

    def __str__(self):
        return f"{self.brand.name}:{self.code}"


class LicenseKey(models.Model):
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name="license_keys")
    customer_email = models.EmailField(db_index=True)
    key = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def generate_key() -> str:
        return "lk_" + secrets.token_urlsafe(24)

    def __str__(self):
        return f"{self.brand.name}:{self.key}"


class License(models.Model):
    STATUS_VALID = "valid"
    STATUS_SUSPENDED = "suspended"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_VALID, "valid"),
        (STATUS_SUSPENDED, "suspended"),
        (STATUS_CANCELLED, "cancelled"),
    ]

    license_key = models.ForeignKey(LicenseKey, on_delete=models.CASCADE, related_name="licenses")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="licenses")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_VALID)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["expires_at"]),
        ]

    def is_active(self) -> bool:
        return self.status == self.STATUS_VALID and self.expires_at > timezone.now()


class Activation(models.Model):
    license = models.ForeignKey(License, on_delete=models.CASCADE, related_name="activations")
    instance_id = models.CharField(max_length=255)  # url/host/machine_id
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["license", "instance_id"], name="uniq_license_instance")
        ]
        indexes = [
            models.Index(fields=["instance_id"]),
        ]

    def revoke(self):
        self.revoked_at = timezone.now()
        self.save(update_fields=["revoked_at"])
