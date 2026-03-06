# Ticket 05: User Addresses

**Priority:** P1  
**Dependencies:** Ticket 00, Ticket 01  
**Estimation:** 1 session

---

## Objective

Implement user address CRUD with types (shipping/billing), default address logic per type, and filtering.

---

## Model: Address

```
Table: addresses

| Field          | Type         | Constraints                    |
|----------------|--------------|-------------------------------|
| id             | Integer      | PK, autoincrement              |
| user_id        | Integer      | FK → users.id, NULLABLE        |
| type           | String(20)   | NOT NULL (values: 'shipping', 'billing') |
| first_name     | String(100)  | NOT NULL                       |
| last_name      | String(100)  | NOT NULL                       |
| company        | String(255)  | NULLABLE                       |
| address_line_1 | String(255)  | NOT NULL                       |
| address_line_2 | String(255)  | NULLABLE                       |
| city           | String(100)  | NOT NULL                       |
| state          | String(100)  | NOT NULL                       |
| postal_code    | String(20)   | NOT NULL                       |
| country        | String(100)  | NOT NULL                       |
| phone          | String(20)   | NULLABLE                       |
| is_default     | Boolean      | NOT NULL, DEFAULT false        |
| created_at     | DateTime     | NOT NULL, DEFAULT now()        |
| updated_at     | DateTime     | NOT NULL, DEFAULT now(), onupdate=now() (SQLAlchemy `onupdate`) |
```

**Note:** `user_id` is NULLABLE because guest orders create temporary addresses with `user_id = null` (see Ticket 06).

---

## Computed fields (in response schema)

- `full_name`: `f"{first_name} {last_name}".strip()`
- `full_address`: `"{address_line_1}, {address_line_2 + ', ' if exists}{city}, {state} {postal_code}, {country}"`

---

## Default logic per type (AddressService)

Implement in the Python service layer (NOT as a DB trigger):

- **When creating** an address with `is_default = True` and `user_id != null`:
  - Deactivate `is_default` on all other addresses of the same `type` for the same `user_id`.
- **When updating** an address changing `is_default` to `True` and `user_id != null`:
  - Deactivate `is_default` on all other addresses of the same `type` for the same `user_id` (excluding the current one).
- Guest addresses (`user_id = null`) have no default logic.
- Defaults of different types can coexist (one default shipping + one default billing per user).

---

## Endpoints

> All require Bearer token. All operations verify that the address belongs to the authenticated user.

### GET /api/v1/user/addresses

**Auth:** Bearer token  
**Query params:**
| Param | Type | Description |
|-------|------|-------------|
| type | string | Filter by type: `shipping` or `billing` (optional) |

**Response 200:**
```json
[
  {
    "id": 1,
    "type": "shipping",
    "first_name": "Juan",
    "last_name": "Pérez",
    "full_name": "Juan Pérez",
    "company": "Acme Corp",
    "address_line_1": "Av. Reforma 123",
    "address_line_2": "Piso 5",
    "city": "Ciudad de México",
    "state": "CDMX",
    "postal_code": "06600",
    "country": "MX",
    "phone": "+5215551234567",
    "is_default": true,
    "full_address": "Av. Reforma 123, Piso 5, Ciudad de México, CDMX 06600, MX",
    "created_at": "...",
    "updated_at": "..."
  }
]
```

**Rules:**
- Only returns addresses belonging to the authenticated user.
- Sort by `is_default DESC, created_at DESC` (defaults first, then most recent).
- If `?type=shipping` is passed, filter by that type only.

---

### POST /api/v1/user/addresses

**Auth:** Bearer token  
**Request body:**
```json
{
  "type": "string (required, 'shipping' or 'billing')",
  "first_name": "string (required)",
  "last_name": "string (required)",
  "company": "string (optional)",
  "address_line_1": "string (required)",
  "address_line_2": "string (optional)",
  "city": "string (required)",
  "state": "string (required)",
  "postal_code": "string (required)",
  "country": "string (required)",
  "phone": "string (optional)",
  "is_default": "boolean (optional, default false)"
}
```

**Response 201:** The created Address object (with computed `full_name` and `full_address`).

---

### GET /api/v1/user/addresses/{id}

**Auth:** Bearer token
**Rules:** If the address does not exist or does not belong to the user → 404.
**Response 200:** The Address object.

---

### PUT /api/v1/user/addresses/{id}

**Auth:** Bearer token
**Request body:** Same fields as POST, all optional (partial update).
**Rules:** If the address does not exist or does not belong to the user → 404.
**Response 200:** The updated Address object.

---

### DELETE /api/v1/user/addresses/{id}

**Auth:** Bearer token
**Rules:** If the address does not exist or does not belong to the user → 404.
**Response:** 204 No Content

---

### PATCH /api/v1/user/addresses/{id}/set-default

**Auth:** Bearer token  
**Rules:**
- If the address does not exist or does not belong to the user → 404.
- Sets `is_default = True` on this address.
- Deactivates `is_default` on other addresses of the same type for the user.

**Response 200:** The updated Address object with `is_default: true`.

---

## Acceptance Criteria

- [ ] Unauthenticated user receives 401
- [ ] List shows only addresses of the authenticated user
- [ ] Filtering by `?type=shipping` works correctly
- [ ] Addresses sorted by default first, then by created_at desc
- [ ] Creating an address with valid data returns 201
- [ ] Required fields are validated (422 if missing)
- [ ] Type must be `shipping` or `billing` (422 if invalid)
- [ ] `full_name` and `full_address` are computed correctly in response
- [ ] Cannot view another user's address (404 — prevents information leakage)
- [ ] Cannot update another user's address (404)
- [ ] Cannot delete another user's address (404)
- [ ] Creating an address as default deactivates other defaults of the same type
- [ ] Updating an address to default deactivates other defaults of the same type
- [ ] Set-default deactivates the previous default of the same type
- [ ] Defaults of different types coexist without conflict
- [ ] Cannot set-default on another user's address (404)
