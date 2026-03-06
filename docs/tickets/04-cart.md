# Ticket 04: Shopping Cart

**Priority:** P1  
**Dependencies:** Ticket 00, Ticket 01, Ticket 03 (Product FK)  
**Estimation:** 2 sessions

---

## Objective

Implement a shopping cart with dual support (authenticated users and guests), guest identification via `X-Session-ID` header, and a cart merge endpoint post-login.

---

## Models

### Cart

```
Table: carts

| Field        | Type         | Constraints                    |
|--------------|--------------|-------------------------------|
| id           | Integer      | PK, autoincrement              |
| user_id      | Integer      | FK → users.id, NULLABLE        |
| session_id   | String(255)  | NULLABLE                       |
| total_items  | Integer      | NOT NULL, DEFAULT 0            |
| total_amount | Decimal(10,2)| NOT NULL, DEFAULT 0.00         |
| expires_at   | DateTime     | NULLABLE                       |
| created_at   | DateTime     | NOT NULL, DEFAULT now()        |
| updated_at   | DateTime     | NOT NULL, DEFAULT now(), onupdate=now() (SQLAlchemy `onupdate`) |
```

**Note:** `total_items` and `total_amount` are stored in the DB but are dynamically recalculated in the API response from the items. The stored value is updated for consistency.

### CartItem

```
Table: cart_items

| Field       | Type          | Constraints                                    |
|-------------|---------------|------------------------------------------------|
| id          | Integer       | PK, autoincrement                               |
| cart_id     | Integer       | FK → carts.id, NOT NULL                         |
| product_id  | Integer       | FK → products.id, NOT NULL                      |
| quantity    | Integer       | NOT NULL                                        |
| unit_price  | Decimal(10,2) | NOT NULL                                        |
| total_price | Decimal(10,2) | NOT NULL                                        |
```

**Constraint:** UNIQUE(`cart_id`, `product_id`) — a product can only appear once per cart.

---

## User/Guest Identification

For each cart request, determine the owner as follows:

1. If there is an `Authorization: Bearer <token>` → authenticated user → find/create cart by `user_id`.
2. If there is NO Bearer token → guest → use `X-Session-ID` header → find/create cart by `session_id`.
3. If there is neither a token nor `X-Session-ID` → return 400.

**Guest carts:**
- Created with `expires_at = now() + 7 days`.
- Expired carts are ignored when searching by session_id.

**User carts:**
- Created with `expires_at = null` (they don't expire).

---

## Endpoints

### GET /api/v1/cart

**Auth:** Bearer token OR `X-Session-ID` header  
**Response 200 (authenticated user):**
```json
{
  "id": 1,
  "user_id": 5,
  "total_items": 3,
  "total_amount": "45.97",
  "items": [
    {
      "id": 10,
      "product_id": 2,
      "product": {
        "id": 2,
        "name": "Reloj Elegante",
        "slug": "reloj-elegante",
        "price": "15.99",
        "stock_quantity": 25,
        "image_url": "https://s3.../products/abc.jpg"
      },
      "quantity": 2,
      "unit_price": "15.99",
      "total_price": "31.98"
    }
  ],
  "summary": {
    "subtotal": "45.97",
    "total_items": 3
  },
  "created_at": "...",
  "updated_at": "..."
}
```

**Response 200 (guest):**
Same format but with `session_id` instead of `user_id`, and includes `expires_at`.

---

### POST /api/v1/cart/items

**Auth:** Bearer token OR `X-Session-ID` header  
**Request body:**
```json
{
  "product_id": "integer (required)",
  "quantity": "integer (required, >= 1)"
}
```

**Response 201:** The full updated cart (same format as GET /cart).

**Business rules:**
- `product_id` existence must be validated against the database inside the API handler or Service layer, throwing a `422 Unprocessable Entity` if it fails (not handled by pure Pydantic).
- If the product is NOT active (`is_active = false`) → 422 with `{ "detail": "Product is not available" }`.
- If there is not enough stock → 422 with `{ "detail": "Insufficient stock" }`.
- If the product **already exists** in the cart → increment the existing CartItem's `quantity` (do NOT create a new one). Re-verify stock with the total quantity.
- `unit_price` is taken from the current `product.price` at the time of adding.
- CartItem `total_price` = `quantity * unit_price`.
- Update Cart's `total_items` and `total_amount` after adding.

---

### PUT /api/v1/cart/items/{cart_item_id}

**Auth:** Bearer token OR `X-Session-ID` header  
**Request body:**
```json
{
  "quantity": "integer (required, >= 1)"
}
```

**Response 200:** The full updated cart.

**Rules:**
- Verify that the CartItem belongs to the current user/guest's cart. If not → 403 with `{ "detail": "Permission denied" }`.
- Verify available stock for the new quantity.
- Recalculate CartItem's `total_price` and Cart totals.

---

### DELETE /api/v1/cart/items/{cart_item_id}

**Auth:** Bearer token OR `X-Session-ID` header  
**Response 200:** The full updated cart.

**Rules:**
- Verify ownership. If it doesn't belong to the user/guest → 403.
- Recalculate Cart totals.

---

### DELETE /api/v1/cart

**Auth:** Bearer token OR `X-Session-ID` header  
**Response 200:** The empty cart (total_items=0, total_amount="0.00", items=[]).

**Rules:**
- Delete all CartItems from the cart.
- Reset totals to 0.

---

### POST /api/v1/cart/merge

**Auth:** Bearer token (REQUIRED, authenticated users only)  
**Request body:**
```json
{
  "session_id": "string (required, guest UUID)"
}
```

**Response 200:** The user's cart with the merged items.

**Business rules:**
1. Find the guest cart by `session_id` (that is not expired).
2. If no guest cart exists → return the user's cart unchanged.
3. For each item in the guest cart:
   - If the product **already exists** in the user's cart → sum the quantities. Verify stock for the total quantity. If not enough → silently discard the guest item.
   - If the product **does not exist** in the user's cart → move it (verifying stock).
4. Delete the guest cart after merging.
5. Recalculate the user's cart totals.

---

## CartService (Business Logic)

Required methods:
- `get_or_create_cart(user_id=None, session_id=None)` → Cart
- `add_item(cart, product_id, quantity)` → Cart (updated)
- `update_item(cart, cart_item_id, quantity)` → Cart
- `remove_item(cart, cart_item_id)` → Cart
- `clear_cart(cart)` → Cart
- `merge_guest_cart(user_cart, session_id)` → Cart
- `update_totals(cart)` → void (recalculates total_items and total_amount)
- `validate_stock(cart)` → list of errors (to verify stock for all items)

---

## Acceptance Criteria

- [ ] Authenticated user gets an empty cart if none exists
- [ ] Guest gets an empty cart with X-Session-ID
- [ ] Adding a valid product returns 201 with updated cart
- [ ] Adding a product with no stock returns 422
- [ ] Adding an inactive product returns 422
- [ ] Adding a non-existent product returns 422 (validation error)
- [ ] Adding quantity ≤ 0 returns 422
- [ ] Adding a product that already exists in the cart increments quantity
- [ ] Updating quantity recalculates total_price
- [ ] Cannot update another user's item (403)
- [ ] Cannot delete another user's item (403)
- [ ] Clearing the cart deletes all items and resets totals
- [ ] Merge correctly combines items by summing quantities
- [ ] Merge silently discards items if stock is insufficient
- [ ] Merge requires Bearer token (401 without token)
- [ ] Expired guest carts are not found
- [ ] Response includes nested product in each item
