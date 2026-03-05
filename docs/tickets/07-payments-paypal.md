# Ticket 07: PayPal Integration + Clear Cart

**Priority:** P1  
**Dependencies:** Ticket 00, Ticket 01, Ticket 04 (Cart), Ticket 06 (Order)  
**Estimate:** 2 sessions

---

## Objective

Implement PayPal API v2 integration to create and capture payments, protected simulation routes, and clear the cart after successful payment.

---

## PayPalService (Business Logic)

```python
class PayPalPaymentService:
    """
    Interacts with PayPal API v2.
    - In real mode: makes HTTP calls to the PayPal API.
    - In simulation mode: generates fake IDs and returns immediate success/failure.
    """
```

### Configuration

| Environment Variable | Description |
|---------------------|-------------|
| `PAYPAL_MODE` | `sandbox` or `live` |
| `PAYPAL_CLIENT_ID` | PayPal Client ID |
| `PAYPAL_CLIENT_SECRET` | PayPal Client Secret |
| `PAYPAL_SIMULATE_PAYMENTS` | `true` for simulation in dev/staging |

**Base URLs:**
- Sandbox: `https://api.sandbox.paypal.com`
- Live: `https://api.paypal.com`

### Service Methods

#### get_access_token() → str
- `POST /v1/oauth2/token` with Basic Auth (`client_id:client_secret`).
- Body: `grant_type=client_credentials`.
- In-memory cache (instance property). Do not persist between requests.
- On failure → raise exception.

#### create_order(order: Order) → dict
- `POST /v2/checkout/orders` with Bearer token.
- Payload:
```json
{
  "intent": "CAPTURE",
  "purchase_units": [{
    "reference_id": "<order_number>",
    "amount": {
      "currency_code": "MXN",
      "value": "<total_amount>",
      "breakdown": {
        "item_total": { "currency_code": "MXN", "value": "<subtotal>" },
        "shipping": { "currency_code": "MXN", "value": "<shipping_cost>" }
      }
    },
    "items": [
      {
        "name": "<product_name>",
        "unit_amount": { "currency_code": "MXN", "value": "<price_per_unit>" },
        "quantity": "<quantity>"
      }
    ],
    "shipping": {
      "name": { "full_name": "<address.full_name>" },
      "address": {
        "address_line_1": "...",
        "address_line_2": "...",
        "admin_area_2": "<city>",
        "admin_area_1": "<state>",
        "postal_code": "...",
        "country_code": "MX"
      }
    }
  }],
  "application_context": {
    "brand_name": "CronosMatic",
    "landing_page": "NO_PREFERENCE",
    "user_action": "PAY_NOW",
    "return_url": "<FRONTEND_URL>/orders/payment/success",
    "cancel_url": "<FRONTEND_URL>/orders/payment/cancel"
  }
}
```
- Returns: `{ "paypal_order_id": "...", "approval_url": "...", "status": "..." }`.

#### capture_order(paypal_order_id: str, order: Order) → dict
- `POST /v2/checkout/orders/{paypal_order_id}/capture` with Bearer token.
- Extracts `capture_id` from the response.
- Returns: `{ "capture_id": "...", "status": "COMPLETED" }`.

#### simulate_success(order: Order) → dict
- Does not make HTTP calls.
- Generates fake IDs: `paypal_order_id = f"SIMULATED_{uuid4().hex[:12]}"`, `capture_id = f"CAPTURE_{uuid4().hex[:12]}"`.
- Returns: `{ "paypal_order_id": "...", "capture_id": "...", "status": "COMPLETED", "simulated": true }`.

#### simulate_failure(order: Order) → dict
- Does not make HTTP calls.
- Generates fake ID: `paypal_order_id = f"FAILED_{uuid4().hex[:12]}"`.
- Returns: `{ "paypal_order_id": "...", "status": "FAILED", "simulated": true, "error": "Payment declined - simulated failure" }`.

---

## Endpoints

### POST /api/v1/payments/paypal/create-order

**Auth:** Bearer token OR `X-Session-ID`  
**Request body:**
```json
{
  "order_id": "integer (required, must exist)"
}
```

**Response 200:**
```json
{
  "paypal_order_id": "5O190127TN364715T",
  "approval_url": "https://www.sandbox.paypal.com/checkoutnow?token=...",
  "order_number": "CM-2026-A1B2C3D4"
}
```

**Validations:**
- Order must exist.
- `payment_status` must be `pending`. If not → 422.

---

### POST /api/v1/payments/paypal/capture-order

**Auth:** Bearer token OR `X-Session-ID`  
**Request body:**
```json
{
  "order_id": "integer (required)",
  "paypal_order_id": "string (required)"
}
```

**Response 200:**
```json
{
  "order_number": "CM-2026-A1B2C3D4",
  "payment_status": "paid",
  "capture_id": "2GG279541U471931P"
}
```

**Internal Flow:**
1. Validate order_id and paypal_order_id.
2. Call `PayPalService.capture_order(paypal_order_id, order)`.
3. Extract `capture_id`.
4. Call `OrderService.update_payment_status(order, 'paid', capture_id, 'paypal')`.
   - This auto-transitions `status` from `pending_payment` → `processing`.
   - This enqueues a confirmation email (see Ticket 08).
5. Call `CartService.clear_cart(cart)` — **CLEAR the cart here after successful payment**.

---

### POST /api/v1/payments/paypal/simulate-success

**Auth:** Bearer token OR `X-Session-ID`  
**Protection:** Only available when `PAYPAL_SIMULATE_PAYMENTS=true`. If `false` → 403 or 404.

**Request body:**
```json
{
  "order_id": "integer (required)"
}
```

**Response 200:**
```json
{
  "order_number": "CM-2026-A1B2C3D4",
  "payment_status": "paid",
  "simulated": true,
  "paypal_order_id": "SIMULATED_abc123def456",
  "capture_id": "CAPTURE_abc123def456"
}
```

**Flow:**
1. Validate `payment_status == pending`.
2. Call `PayPalService.simulate_success(order)`.
3. Call `OrderService.update_payment_status(order, 'paid', capture_id, 'paypal')`.
4. Clear cart.

---

### POST /api/v1/payments/paypal/simulate-failure

**Auth:** Bearer token OR `X-Session-ID`  
**Protection:** Only available when `PAYPAL_SIMULATE_PAYMENTS=true`.

**Request body:**
```json
{
  "order_id": "integer (required)"
}
```

**Response 200:**
```json
{
  "order_number": "CM-2026-A1B2C3D4",
  "payment_status": "failed",
  "simulated": true,
  "paypal_order_id": "FAILED_abc123def456",
  "error": "Payment declined - simulated failure"
}
```

**Flow:**
1. Validate `payment_status == pending`.
2. Call `PayPalService.simulate_failure(order)`.
3. Call `OrderService.update_payment_status(order, 'failed', paypal_order_id, 'paypal')`.
4. **DO NOT cancel the order or restore stock here.** The user may retry.

---

### GET /api/v1/payments/paypal/verify-config

**Auth:** Bearer token OR `X-Session-ID`  
**Response 200:**
```json
{
  "mode": "sandbox",
  "client_id_configured": true,
  "client_secret_configured": true,
  "simulate_payments": true,
  "base_url": "https://api.sandbox.paypal.com",
  "auth_test": "success"
}
```

**Flow:** Attempts to obtain an access token. On failure, returns `auth_test: "failed"` with the error.

---

## Full Flow for React

```
1. React calls POST /api/v1/orders → creates order with status pending_payment
2. React calls POST /payments/paypal/create-order → gets approval_url
3. React redirects the user to PayPal (approval_url)
4. User approves on PayPal → PayPal redirects to return_url with token and PayerID
5. React extracts the paypal_order_id from the token/URL
6. React calls POST /payments/paypal/capture-order → payment captured
7. Backend updates status, sends email, clears cart
8. React displays confirmation
```

---

## Acceptance Criteria

- [ ] Create-order generates a PayPal order and returns approval_url
- [ ] Only orders with `payment_status=pending` can be processed
- [ ] Capture-order captures the payment and updates the order
- [ ] After successful capture, status changes to `processing` and payment_status to `paid`
- [ ] After successful capture, the cart is cleared
- [ ] Simulate-success works only when `PAYPAL_SIMULATE_PAYMENTS=true`
- [ ] Simulate-failure works only when `PAYPAL_SIMULATE_PAYMENTS=true`
- [ ] With `PAYPAL_SIMULATE_PAYMENTS=false`, simulate endpoints return 403/404
- [ ] Verify-config reports PayPal configuration status
- [ ] PayPal API errors are handled gracefully with descriptive messages
- [ ] Access token is obtained correctly via Basic Auth
- [ ] Currency hardcoded as `MXN`, country_code as `MX`
