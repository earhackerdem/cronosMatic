import base64
from uuid import uuid4

import httpx

from app.config import settings
from app.domain.order.entity import Order


class PayPalAuthError(ValueError):
    """Token acquisition failure."""


class PayPalAPIError(ValueError):
    """API call failure."""


class PayPalPaymentService:
    def __init__(self) -> None:
        self._access_token: str | None = None
        if settings.paypal_mode == "live":
            self._base_url = "https://api.paypal.com"
        else:
            self._base_url = "https://api.sandbox.paypal.com"

    async def get_access_token(self) -> str:
        if self._access_token:
            return self._access_token
        credentials = base64.b64encode(
            f"{settings.paypal_client_id}:{settings.paypal_client_secret}".encode()
        ).decode()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/v1/oauth2/token",
                headers={
                    "Authorization": f"Basic {credentials}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data="grant_type=client_credentials",
            )
        if resp.status_code != 200:
            raise PayPalAuthError(f"Failed to obtain access token: {resp.text}")
        data = resp.json()
        if "access_token" not in data:
            raise PayPalAuthError("access_token not found in PayPal response")
        self._access_token = data["access_token"]
        return self._access_token

    async def create_order(self, order: Order, shipping_address: dict) -> dict:
        """Create a PayPal order. In simulate mode, skip HTTP calls."""
        if settings.paypal_simulate_payments:
            fake_id = f"SIMULATED_{uuid4().hex[:12]}"
            return {
                "paypal_order_id": fake_id,
                "approval_url": f"https://www.sandbox.paypal.com/checkoutnow?token={fake_id}",
                "status": "CREATED",
            }

        token = await self.get_access_token()
        currency = settings.payment_currency
        country = settings.payment_country_code

        items = [
            {
                "name": item.product_name,
                "unit_amount": {
                    "currency_code": currency,
                    "value": str(item.price_per_unit),
                },
                "quantity": str(item.quantity),
            }
            for item in order.items
        ]

        payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": order.order_number,
                    "amount": {
                        "currency_code": currency,
                        "value": str(order.total_amount),
                        "breakdown": {
                            "item_total": {
                                "currency_code": currency,
                                "value": str(order.subtotal_amount),
                            },
                            "shipping": {
                                "currency_code": currency,
                                "value": str(order.shipping_cost),
                            },
                        },
                    },
                    "items": items,
                    "shipping": {
                        "name": {
                            "full_name": (
                                f"{shipping_address['first_name']} {shipping_address['last_name']}"
                            )
                        },
                        "address": {
                            "address_line_1": shipping_address["address_line_1"],
                            "address_line_2": shipping_address.get(
                                "address_line_2", ""
                            ),
                            "admin_area_2": shipping_address["city"],
                            "admin_area_1": shipping_address["state"],
                            "postal_code": shipping_address["postal_code"],
                            "country_code": country,
                        },
                    },
                }
            ],
            "application_context": {
                "brand_name": "CronosMatic",
                "landing_page": "NO_PREFERENCE",
                "user_action": "PAY_NOW",
                "return_url": f"{settings.frontend_url}/orders/payment/success",
                "cancel_url": f"{settings.frontend_url}/orders/payment/cancel",
            },
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/v2/checkout/orders",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        if resp.status_code not in (200, 201):
            raise PayPalAPIError(f"PayPal create order failed: {resp.text}")

        data = resp.json()
        approval_url = next(
            (
                link["href"]
                for link in data.get("links", [])
                if link["rel"] == "approve"
            ),
            None,
        )
        return {
            "paypal_order_id": data["id"],
            "approval_url": approval_url or "",
            "status": data.get("status", ""),
        }

    async def capture_order(self, paypal_order_id: str) -> dict:
        """Capture a PayPal order. In simulate mode, skip HTTP calls."""
        if settings.paypal_simulate_payments:
            capture_id = f"CAPTURE_{uuid4().hex[:12]}"
            return {"capture_id": capture_id, "status": "COMPLETED"}

        token = await self.get_access_token()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/v2/checkout/orders/{paypal_order_id}/capture",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
        if resp.status_code not in (200, 201):
            raise PayPalAPIError(f"PayPal capture failed: {resp.text}")

        data = resp.json()
        capture_id = data["purchase_units"][0]["payments"]["captures"][0]["id"]
        return {"capture_id": capture_id, "status": "COMPLETED"}

    def simulate_success(self, order: Order) -> dict:
        paypal_order_id = f"SIMULATED_{uuid4().hex[:12]}"
        capture_id = f"CAPTURE_{uuid4().hex[:12]}"
        return {
            "paypal_order_id": paypal_order_id,
            "capture_id": capture_id,
            "status": "COMPLETED",
            "simulated": True,
        }

    def simulate_failure(self, order: Order) -> dict:
        paypal_order_id = f"FAILED_{uuid4().hex[:12]}"
        return {
            "paypal_order_id": paypal_order_id,
            "status": "FAILED",
            "simulated": True,
            "error": "Payment declined - simulated failure",
        }
