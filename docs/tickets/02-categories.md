# Ticket 02: Category Catalog

**Priority:** P1  
**Dependencies:** Ticket 00, Ticket 01 (for admin CRUD)  
**Estimation:** 1 session

---

## Objective

Implement the Category model with public endpoints (active categories only) and admin CRUD (all categories).

---

## Model: Category

```
Table: categories

| Field       | Type         | Constraints                    |
|-------------|--------------|-------------------------------|
| id          | Integer      | PK, autoincrement              |
| name        | String(255)  | NOT NULL                       |
| slug        | String(255)  | NOT NULL, UNIQUE               |
| description | Text         | NULLABLE                       |
| image_path  | String(500)  | NULLABLE                       |
| is_active   | Boolean      | NOT NULL, DEFAULT true         |
| created_at  | DateTime     | NOT NULL, DEFAULT now()        |
| updated_at  | DateTime     | NOT NULL, DEFAULT now(), onupdate=now() (SQLAlchemy `onupdate`) |
```

**Relations:**
- `Category` has many `Product` (see Ticket 03)

---

## Computed field: image_url

In the **response schema** (Pydantic), include `image_url`:
- If `image_path` is `null` → return `null`.
- If `image_path` starts with `http` → return as-is.
- Otherwise → return the full S3 URL (or concatenate with the storage base URL).

---

## Public Endpoints

### GET /api/v1/categories

**Auth:** public  
**Response 200:**
```json
{
  "items": [
    {
      "id": 1,
      "name": "Relojes de Bolsillo",
      "slug": "relojes-de-bolsillo",
      "description": "Description...",
      "image_path": "categories/abc.jpg",
      "image_url": "https://s3.../categories/abc.jpg",
      "is_active": true,
      "created_at": "2026-03-05T12:00:00Z",
      "updated_at": "2026-03-05T12:00:00Z"
    }
  ],
  "total": 3,
  "page": 1,
  "pages": 1,
  "size": 10
}
```

**Rules:**
- Only returns categories with `is_active = true`.
- Paginated. Default `size = 10`.

---

### GET /api/v1/categories/{slug}

**Auth:** public  
**Response 200:**
```json
{
  "category": {
    "id": 1,
    "name": "Relojes de Bolsillo",
    "slug": "relojes-de-bolsillo",
    "description": "...",
    "image_path": "categories/abc.jpg",
    "image_url": "https://s3.../categories/abc.jpg",
    "is_active": true,
    "created_at": "...",
    "updated_at": "..."
  },
  "products": {
    "items": [...],
    "total": 15,
    "page": 1,
    "pages": 2,
    "size": 10
  }
}
```

**Rules:**
- Look up by `slug`, not by ID.
- If the category is NOT active (`is_active = false`), return 404 with `{ "detail": "Category not found." }`.
- Includes the ACTIVE products of the category, paginated (default `size = 10`).
- Inactive products of the category are NOT included.

---

## Admin Endpoints

> All require Bearer token + `require_admin` dependency.

### GET /api/v1/admin/categories

**Auth:** admin  
**Response 200:** Paginated `{ items, total, page, pages, size }`

**Rules:**
- Returns ALL categories (including inactive ones). Does not filter by `is_active`.
- Default `size = 15`.

---

### POST /api/v1/admin/categories

**Auth:** admin  
**Request body:**
```json
{
  "name": "string (required)",
  "slug": "string (required, unique)",
  "description": "string (optional)",
  "image_path": "string (optional)",
  "is_active": "boolean (optional, default true)"
}
```

**Response 201:** The created Category object.

---

### GET /api/v1/admin/categories/{id}

**Auth:** admin  
**Response 200:** The Category object (by numeric ID).

**Errors:**
- 404: category not found.

---

### PUT /api/v1/admin/categories/{id}

**Auth:** admin  
**Request body:** Same fields as POST, all optional (partial update).  
**Response 200:** The updated Category object.

**Validation:**
- If `slug` is provided, verify uniqueness (excluding the current record).

---

### DELETE /api/v1/admin/categories/{id}

**Auth:** admin  
**Response:** 204 No Content

**Rules:**
- Performs a soft delete: sets `is_active = false` instead of removing the record from the database.
- This prevents foreign key constraints from failing in the `products` table while safely hiding the category.

---

## Acceptance Criteria

- [ ] `GET /categories` only returns active categories
- [ ] `GET /categories/{slug}` returns active category with paginated active products
- [ ] `GET /categories/{slug}` for an inactive category returns 404
- [ ] Inactive products do NOT appear in the category's product list
- [ ] Category products are paginated (default 10/page)
- [ ] Admin can list ALL categories (including inactive ones)
- [ ] Admin can create, view, update, and delete categories
- [ ] Non-admin receives 403 on admin endpoints
- [ ] Slug is unique in the DB
- [ ] `image_url` is `null` when `image_path` is null
- [ ] `image_url` returns the full URL when `image_path` exists
