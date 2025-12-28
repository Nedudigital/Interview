from dataclasses import dataclass
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import Brand

@dataclass
class BrandPrincipal:
    brand: Brand

    @property
    def is_authenticated(self) -> bool:
        return True

class BrandAPIKeyAuthentication(BaseAuthentication):
    header_name = "X-API-Key"

    def authenticate(self, request):
        api_key = request.headers.get(self.header_name)
        if not api_key:
            return None  # unauthenticated

        try:
            brand = Brand.objects.get(api_key=api_key)
        except Brand.DoesNotExist:
            raise AuthenticationFailed("Invalid API key")

        return (BrandPrincipal(brand=brand), api_key)
