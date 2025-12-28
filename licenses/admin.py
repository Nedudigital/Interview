from django.contrib import admin
from .models import Brand, Product, LicenseKey, License, Activation

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "api_key")
    search_fields = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "brand", "code", "name")
    list_filter = ("brand",)
    search_fields = ("code", "name")


@admin.register(LicenseKey)
class LicenseKeyAdmin(admin.ModelAdmin):
    list_display = ("id", "brand", "key", "customer_email", "created_at")
    search_fields = ("key", "customer_email")
    list_filter = ("brand",)

@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "status", "expires_at", "license_key", "created_at")
    list_filter = ("status", "product__brand")
    search_fields = ("license_key__key", "license_key__customer_email")

@admin.register(Activation)
class ActivationAdmin(admin.ModelAdmin):
    list_display = ("id", "license", "instance_id", "created_at", "revoked_at")
    search_fields = ("instance_id", "license__license_key__key")
