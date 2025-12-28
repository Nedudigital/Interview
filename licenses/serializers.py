from rest_framework import serializers
from .models import Product


class ProvisionLicenseSerializer(serializers.Serializer):
    customer_email = serializers.EmailField()
    product_codes = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False
    )

    def validate_product_codes(self, codes):
        brand = self.context["brand"]
        products = Product.objects.filter(brand=brand, code__in=codes)

        if products.count() != len(codes):
            raise serializers.ValidationError("One or more products not found for this brand")

        return list(products)


class ActivateSerializer(serializers.Serializer):
    license_key = serializers.CharField()
    instance_id = serializers.CharField()
