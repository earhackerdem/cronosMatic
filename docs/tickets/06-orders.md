# Ticket 06: Orders and Stock Management

**Priority:** P1  
**Dependencies:** Ticket 00, Ticket 01, Ticket 03 (Product), Ticket 04 (Cart), Ticket 05 (Address)  
**Estimation:** 2-3 sessions

---

## Objective

Implement order creation from cart, stock reservation pattern, order and payment statuses, cancellation with stock restoration, and order history queries.

---

## Models

### Order

```
Table: orders

| Field               | Type          | Constraints                    |
|---------------------|---------------|-------------------------------|
| id                  | Integer       | PK, autoincrement              |
| user_id             | Integer       | FK → users.id, NULLABLE        |
| guest_email         | String(255)   | NULLABLE                       |
| order_number        | String(50)    | NOT NULL, UNIQUE               |
| shipping_address_id | Integer       | FK → addresses.id, NOT NULL    |
| billing_address_id  | Integer       | FK → addresses.id, NULLABLE    |
| status              | String(20)    | NOT NULL                       |
| subtotal_amount     | Decimal(10,2) | NOT NULL                       |
| shipping_cost       | Decimal(10,2) | NOT NULL, DEFAULT 0.00         |
| total_amount        | Decimal(10,2) | NOT NULL                       |
| payment_gateway     | String(50)    | NULLABLE                       |
| payment_id          | String(255)   | NULLABLE                       |
| payment_status      | String(20)    | NOT NULL                       |
| shipping_method_name| String(100)   | NULLABLE                       |
| notes               | Text          | NULLABLE                       |
| created_at          | DateTime      | NOT NULL, DEFAULT now()        |
| updated_at          | DateTime      | NOT NULL, DEFAULT now()        |
```

### OrderItem

```
Table: order_items

| Field          | Type          | Constraints                    |
|----------------|---------------|-------------------------------|
| id             | Integer       | PK, autoincrement              |
| order_id       | Integer       | FK → orders.id, NOT NULL       |
| product_id     | Integer       | FK → products.id, NULLABLE     |
| product_name   | String(255)   | NOT NULL                       |
| quantity       | Integer       | NOT NULL                       |
| price_per_unit | Decimal(10,2) | NOT NULL                       |
| total_price    | Decimal(10,2) | NOT NULL                       |
| created_at     | DateTime      | NOT NULL, DEFAULT now()        |
| updated_at     | DateTime      | NOT NULL, DEFAULT now()        |
```

**Rule:** `total_price` is auto-calculated as `quantity * price_per_unit` before saving.

---

## Status Enums (StrEnum in Python)

### OrderStatus
| Value | Meaning |
|-------|---------|
| `pending_payment` | Pending payment |
| `processing` | Processing |
| `shipped` | Shipped |
| `delivered` | Delivered |
| `cancelled` | Cancelled |

### PaymentStatus
| Value | Meaning |
|-------|---------|
| `pending` | Pending |
| `paid` | Paid |
| `failed` | Failed |
| `refunded` | Refunded |

---

## Order number format

`CM-{YEAR}-{RANDOM_8_CHARS}` — example: `CM-2026-A1B2C3D4`

- Use `secrets.token_hex(4).upper()` for the 8 characters.
- Verify uniqueness in DB (retry loop until a unique one is found).

---

## Computed fields (response schema)

- `email`: `user.email if user else guest_email`
- `status_label`: human-readable label for the status (for admin/dashboards)
- `payment_status_label`: human-readable label for the payment_status

---

## Stock Reservation Pattern


1. **When creating an order:** Use `SELECT ... FOR UPDATE` on the involved products (pessimistic locking). Verify available stock. Mark stock as reserved (decrement `stock_quantity`). If any product doesn't have enough stock → rollback and 422 error.
2. **When confirming payment (payment_status → paid):** Stock was already decremented. Just change status.
3. **If payment fails or is cancelled:** Restore stock by incrementing `stock_quantity` of each product.

> **Note:** In this implementation, "reserving" and "decrementing" are equivalent — stock is decremented when the order is created, within a transaction with `FOR UPDATE` to prevent race conditions. If the order is cancelled, stock is restored.

---

## Endpoints

### POST /api/v1/orders

**Auth:** Bearer token OR `X-Session-ID` header (supports both flows)  
**Request body (authenticated user):**
```json
{
  "shipping_address_id": "integer (required, must exist and belong to user)",
  "billing_address_id": "integer (optional, defaults to shipping_address_id)",
  "payment_method": "string (required, only 'paypal' supported currently)",
  "shipping_method_name": "string (optional)",
  "notes": "string (optional)"
}
```

**Request body (guest):**
```json
{
  "guest_email": "string (required for guests, valid email)",
  "shipping_address": {
    "first_name": "string (required)",
    "last_name": "string (required)",
    "company": "string (optional)",
    "address_line_1": "string (required)",
    "address_line_2": "string (optional)",
    "city": "string (required)",
    "state": "string (required)",
    "postal_code": "string (required)",
    "country": "string (required)",
    "phone": "string (optional)"
  },
  "billing_address": {
    "...same fields (optional, defaults to shipping_address)"
  },
  "payment_method": "string (required)",
  "shipping_method_name": "string (optional)",
  "notes": "string (optional)"
}
```

**Response 201:**
```json
{
  "order": {
    "id": 1,
    "order_number": "CM-2026-A1B2C3D4",
    "status": "pending_payment",
    "payment_status": "pending",
    "subtotal_amount": "1400.00",
    "shipping_cost": "100.00",
    "total_amount": "1500.00",
    "items": [
      {
        "id": 1,
        "product_id": 5,
        "product_name": "Reloj Elegante",
        "quantity": 1,
        "price_per_unit": "1400.00",
        "total_price": "1400.00"
      }
    ],
    "created_at": "..."
  },
  "payment": {
    "method": "paypal",
    "status": "pending"
  }
}
```

**Internal flow:**
1. Identify user (JWT) or guest (X-Session-ID).
2. Get cart. If empty → 422.
3. Validate stock for all items (with `FOR UPDATE`).
4. If guest: create two records in `addresses` (shipping + billing) with `user_id = null`.
5. If billing_address was not provided: use shipping_address.
6. Set `shipping_cost` using the `DEFAULT_SHIPPING_COST` environment variable. `total_amount = subtotal_amount + shipping_cost`.
7. Create `Order` with `status = pending_payment`, `payment_status = pending`.
8. Create `OrderItems` from `CartItems`. Copy `product.name` to `product_name`, `product.price` to `price_per_unit`.
9. Decrement stock for each product.
10. All within a DB transaction.
11. **Do NOT clear the cart here.** The cart is cleared after successful payment (see Ticket 07).

**Errors:**
- 422: empty cart, insufficient stock, address not found, invalid payment_method, guest_email required for guests.

---

### GET /api/v1/user/orders

**Auth:** Bearer token  
**Query params:** `?page=1&size=10`  
**Response 200:** Paginated `{ items, total, page, pages, size }`

Each order includes: `id`, `order_number`, `status`, `payment_status`, `total_amount`, `created_at`, and item count.

---

### GET /api/v1/user/orders/{order_number}

**Auth:** Bearer token  
**Rules:** Look up by `order_number` (NOT by ID). Verify that the order belongs to the user. If not → 403.  
**Response 200:** Complete order with items, shipping address, and billing address.

---

## OrderService (Business Logic)

Required methods:
- `create_order_from_cart(cart, user_id, guest_email, shipping_address_id, billing_address_id, payment_method, ...)` → Order
- `update_status(order, new_status)` → Order
- `update_payment_status(order, payment_status, payment_id, payment_gateway)` → Order
  - If `payment_status = paid` and `status == pending_payment` → auto-transition to `processing`.
  - Triggers email confirmation (see Ticket 08).
- `cancel_order(order, reason)` → Order
  - Only if `status` is `pending_payment` or `processing`.
  - Restore stock for each OrderItem.
  - Append reason to the `notes` field.
  - *Note: Abandoned orders in `pending_payment` status will be automatically cancelled by a Celery Beat background task to release reserved stock (see Ticket 08).*
- `get_user_orders(user_id, page, size)` → paginated results
- `get_order_by_number(order_number, user_id)` → Order or None
- `generate_order_number()` → string (format CM-YYYY-XXXXXXXX, unique)

**canBeCancelled rule:** Only orders in `pending_payment` or `processing` can be cancelled. `shipped`, `delivered`, `cancelled` → cannot be cancelled.

---

## Acceptance Criteria

- [ ] Authenticated user can create an order with an existing shipping_address_id
- [ ] Guest can create an order with guest_email and addresses in body
- [ ] Cannot create an order with an empty cart (422)
- [ ] Cannot create an order with insufficient stock (422)
- [ ] Stock is decremented when creating an order (within a transaction with FOR UPDATE)
- [ ] If billing_address_id is not provided, uses shipping_address_id
- [ ] Order number has format CM-YYYY-XXXXXXXX and is unique
- [ ] OrderItem.total_price is calculated automatically
- [ ] User orders are listed with pagination
- [ ] Viewing an order by order_number verifies ownership
- [ ] Status enum uses English values
- [ ] `update_payment_status(paid)` auto-transitions status to `processing`
- [ ] `cancel_order` restores stock for each product
- [ ] `cancel_order` fails for shipped/delivered/cancelled orders
- [ ] The cart is NOT cleared in this ticket (cleared in Ticket 07 post-payment)
