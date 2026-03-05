# Ticket 03: Product Catalog + Image Upload

**Priority:** P1  
**Dependencies:** Ticket 00, Ticket 01 (admin), Ticket 02 (Category FK)  
**Estimation:** 1-2 sessions

---

## Objective

Implement the Product model with public endpoints (filtering, search, sorting), admin CRUD, and image upload to S3.

---

## Model: Product

```
Table: products

| Field          | Type          | Constraints                    |
|----------------|---------------|-------------------------------|
| id             | Integer       | PK, autoincrement              |
| category_id    | Integer       | FK → categories.id, NOT NULL   |
| name           | String(255)   | NOT NULL                       |
| slug           | String(255)   | NOT NULL, UNIQUE               |
| sku            | String(100)   | NOT NULL, UNIQUE               |
| description    | Text          | NULLABLE                       |
| price          | Decimal(10,2) | NOT NULL                       |
| stock_quantity | Integer       | NOT NULL, DEFAULT 0            |
| brand          | String(255)   | NULLABLE                       |
| movement_type  | String(100)   | NULLABLE                       |
| image_path     | String(500)   | NULLABLE                       |
| is_active      | Boolean       | NOT NULL, DEFAULT true         |
| created_at     | DateTime      | NOT NULL, DEFAULT now()        |
| updated_at     | DateTime      | NOT NULL, DEFAULT now()        |
```

**Relations:**
- `Product` belongs to `Category`
- `Product` has many `OrderItem` (see Ticket 06)
- `Product` has many `CartItem` (see Ticket 04)

---

## Computed field: image_url

In the **response schema** (Pydantic), include `image_url`:
- If `image_path` is `null` → return `null`.
- If `image_path` starts with `http` → return as-is.
- Otherwise → return the full S3 URL (or concatenate with the storage base URL).

**There is NO fallback to hardcoded images.** The React frontend handles the placeholder.

---

## Public Endpoints

### GET /api/v1/products

**Auth:** public  
**Query params:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| category | string | - | Filter by active category slug |
| search | string | - | Search in name, description, SKU |
| sortBy | string | created_at | Options: `name`, `price`, `created_at` |
| sortDirection | string | desc | Options: `asc`, `desc` |
| page | int | 1 | Current page |
| size | int | 12 | Items per page |

**Response 200:**
```json
{
  "items": [
    {
      "id": 1,
      "category_id": 1,
      "category": {
        "id": 1,
        "name": "Relojes de Pulsera",
        "slug": "relojes-de-pulsera"
      },
      "name": "Reloj Elegante",
      "slug": "reloj-elegante",
      "sku": "RE-001",
      "description": "...",
      "price": "1500.00",
      "stock_quantity": 25,
      "brand": "CronosMatic",
      "movement_type": "Automatic",
      "image_path": "products/abc.jpg",
      "image_url": "https://s3.../products/abc.jpg",
      "is_active": true,
      "created_at": "...",
      "updated_at": "..."
    }
  ],
  "total": 20,
  "page": 1,
  "pages": 2,
  "size": 12
}
```

**Rules:**
- Only returns products with `is_active = true`.
- If the `category` param is a slug of an INACTIVE category → return 422 with an error on the `category` field.
- Search via `search` applies `ILIKE` on `name`, `description`, and `sku`.
- Include a nested `category` object (id, name, slug) in each product.

---

### GET /api/v1/products/{slug}

**Auth:** public  
**Response 200:**
```json
{
  "data": {
    "id": 1,
    "category": { "id": 1, "name": "...", "slug": "..." },
    "name": "Reloj Elegante",
    "slug": "reloj-elegante",
    "sku": "RE-001",
    "description": "...",
    "price": "1500.00",
    "stock_quantity": 25,
    "brand": "CronosMatic",
    "movement_type": "Automatic",
    "image_path": "products/abc.jpg",
    "image_url": "https://s3.../products/abc.jpg",
    "is_active": true,
    "created_at": "...",
    "updated_at": "..."
  }
}
```

**Rules:**
- Look up by `slug`, not by ID.
- If the product is NOT active → return 422 with an error on the `slug` field.

---

## Admin Endpoints

> All require Bearer token + `require_admin` dependency.

### GET /api/v1/admin/products

**Auth:** admin  
**Response 200:** Paginated. Shows ALL products (including inactive ones). Default `size = 15`.

---

### POST /api/v1/admin/products

**Auth:** admin  
**Request body:**
```json
{
  "category_id": "integer (required, must exist)",
  "name": "string (required)",
  "sku": "string (required, unique)",
  "description": "string (optional)",
  "price": "decimal (required, > 0)",
  "stock_quantity": "integer (required, >= 0)",
  "brand": "string (optional)",
  "movement_type": "string (optional)",
  "image_path": "string (optional, path already uploaded via upload endpoint)",
  "is_active": "boolean (optional, default true)"
}
```

**Response 201:** The created product.

---

### GET /api/v1/admin/products/{id}

**Auth:** admin  
**Response 200:** Product by numeric ID (includes inactive ones).

---

### PUT /api/v1/admin/products/{id}

**Auth:** admin  
**Request body:** Same fields as POST, all optional.  
**Validation:** If `sku` is provided, verify uniqueness (excluding the current record).  
**Response 200:** The updated product.

---

### DELETE /api/v1/admin/products/{id}

**Auth:** admin  
**Response:** 204 No Content

---

## Endpoint: Image Upload

### POST /api/v1/admin/images/upload

**Auth:** admin  
**Content-Type:** `multipart/form-data`  
**Request:**
| Field | Type | Description |
|-------|------|-------------|
| image | File | Image file (required) |
| type | string | Subdirectory: `products` or `categories` (default: `products`) |

**Response 201:**
```json
{
  "data": {
    "path": "products/a1b2c3d4-uuid.jpg",
    "url": "https://s3.amazonaws.com/bucket/products/a1b2c3d4-uuid.jpg"
  }
}
```

**Rules:**
- Generate a UUID for the filename.
- Upload to the S3 bucket in the `{type}/` subdirectory.
- Validate that the file is an image (mime type: `image/jpeg`, `image/png`, `image/webp`, `image/gif`).
- Maximum size: 5MB.

---

## Acceptance Criteria

- [ ] `GET /products` only returns active products
- [ ] `GET /products` supports filtering by category (slug), search, and sorting
- [ ] Filtering by an inactive category returns 422
- [ ] Search works on name, description, and SKU
- [ ] Sorting works by name, price, created_at (asc/desc)
- [ ] `GET /products/{slug}` for an inactive product returns 422
- [ ] `image_url` is `null` when `image_path` is null
- [ ] `image_url` returns the full URL when `image_path` exists
- [ ] Admin can perform full CRUD on products
- [ ] Admin sees all products including inactive ones
- [ ] SKU is unique (validated on create and update)
- [ ] Image upload uploads to S3 with a UUID filename
- [ ] Image upload validates mime type and size
- [ ] Non-admin receives 403 on admin endpoints
