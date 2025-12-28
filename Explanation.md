# Centralized License Service – Explanation

## 1. Problem Overview (In My Own Words)

group.one operates multiple independent products across multiple brands (e.g. RankMath, WP Rocket, Content AI).
Each brand currently manages its own users, billing, and subscriptions, but there is no single authoritative system that defines what a customer is entitled to use.

This project implements a centralized **License Service** that becomes the **single source of truth** for:
- License keys
- Product entitlements (licenses)
- License lifecycle state (valid / suspended / cancelled + expiration)
- Runtime activations per instance (site URL, machine ID, host, etc.)

Brand systems integrate with this service to provision and manage licenses, while end-user products (plugins/apps/CLI) integrate with it to activate and check licenses.

No UI is required; the system is operated purely through APIs.

---

## 2. Architecture & High-Level Design

### Tech Stack
- Python 3.12
- Django + Django REST Framework
- PostgreSQL (recommended) or SQLite for local dev
- Stateless HTTP APIs

### Core Domain Models
- **Brand**: Represents a tenant (e.g. RankMath, WP Rocket). Each brand owns its own products and API key.
- **Product**: Licensable product owned by a Brand (e.g. `rankmath`, `content_ai`, `wp_rocket`).
- **LicenseKey**: A customer-facing key, scoped to `(brand, customer_email)`. One key can unlock multiple products *within the same brand*.
- **License**: A product entitlement under a LicenseKey, with `status` and `expires_at`.
- **Activation**: Represents an activated instance for a license (e.g. `https://example.com`). Can be revoked/deactivated.

### Core Design Principles
- **Multi-tenant by design**: brand is a first-class boundary.
- **Entitlements separated from activations**: a customer can be entitled without being activated, and activation is tracked explicitly.
- **Brand-integrable APIs**: brand systems can provision and lifecycle licenses.
- **Product-facing APIs**: end-user products can activate/check licenses.
- **Extensible**: seat limits, device fingerprinting, stronger auth, and lifecycle operations can be added without rewriting the data model.

---

## 3. Multi-Tenancy Model

- Each **Brand** is a tenant.
- Products are scoped to a single brand.
- License keys are scoped to `(brand, customer_email)`:
  - This supports “one license key per brand per customer”
  - And allows “addons under the same brand key” (RankMath + Content AI share one key)
- Licenses do not cross brands. A customer owning products in multiple brands will have multiple license keys.

Why this is good:
- Brand systems remain independent for billing/users, but licensing/entitlements become centralized.
- No cross-brand leakage (a RankMath key cannot unlock WP Rocket).
- Easy to report “all entitlements by email across brands” through an internal-only endpoint.

---

## 4. Authentication & Authorization Model

### Brand APIs (Provision + Internal Listing + Lifecycle)
- Auth: `X-API-Key: <brand_api_key>`
- Implemented via a DRF authentication class that resolves the Brand principal.
- Protected endpoints use `IsAuthenticated`.

### End-User Product APIs (Activate + Check)
For this exercise:
- Activate and Check are unauthenticated to keep the core slice minimal and focused.

In production, I would add:
- HMAC-signed requests (brand/product shared secrets) OR OAuth client credentials
- Rate limiting (per key + per IP)
- Abuse detection (brute force / key guessing)
- Audit logs for every activation/check
- Optional per-product secrets (so leaked secrets don’t expose all brands)

---

## 5. API Endpoints (Implemented)

Base path: `/api/v1`

### US1 – Brand provisions a license (Implemented)
`POST /api/v1/licenses/provision/`

Headers:
- `X-API-Key: <brand_api_key>`
- `Content-Type: application/json`

Body:
```json
{
  "customer_email": "buyer@example.com",
  "product_codes": ["rankmath", "content_ai"]
}
