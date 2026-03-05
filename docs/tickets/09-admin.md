# Ticket 09: Admin Consolidation

**Priority:** P2  
**Dependencies:** Ticket 01, Ticket 02, Ticket 03  
**Estimate:** 0.5 sessions

---

## Objective

Verify and consolidate that all admin endpoints work correctly under the `require_admin` dependency. This ticket does NOT create new logic — it verifies that admin endpoints from Tickets 02 and 03 are correctly protected and documented.

---

## Verification Checklist

### Admin Categories (from Ticket 02)
- [ ] `GET /api/v1/admin/categories` → requires `require_admin`
- [ ] `POST /api/v1/admin/categories` → requires `require_admin`
- [ ] `GET /api/v1/admin/categories/{id}` → requires `require_admin`
- [ ] `PUT /api/v1/admin/categories/{id}` → requires `require_admin`
- [ ] `DELETE /api/v1/admin/categories/{id}` → requires `require_admin`
- [ ] Admin GET lists ALL categories (including inactive ones)
- [ ] Non-admin receives 403 on all endpoints

### Admin Products (from Ticket 03)
- [ ] `GET /api/v1/admin/products` → requires `require_admin`
- [ ] `POST /api/v1/admin/products` → requires `require_admin`
- [ ] `GET /api/v1/admin/products/{id}` → requires `require_admin`
- [ ] `PUT /api/v1/admin/products/{id}` → requires `require_admin`
- [ ] `DELETE /api/v1/admin/products/{id}` → requires `require_admin`
- [ ] Admin GET lists ALL products (including inactive ones)
- [ ] Non-admin receives 403 on all endpoints

### Admin Image Upload (from Ticket 03)
- [ ] `POST /api/v1/admin/images/upload` → requires `require_admin`
- [ ] Non-admin receives 403

---

## require_admin Dependency (from Ticket 01)

Implementation reminder:

```python
async def require_admin(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail={"message": "Forbidden. User is not an administrator."}
        )
    return current_user
```

---

## Admin Integration Tests

Create tests that verify the full flow:

1. **Setup:** Create an admin user (`is_admin=True`) and a regular user.
2. **For each admin endpoint:** Verify that:
   - With admin token → 200/201/204.
   - With regular user token → 403.
   - Without token → 401.

---

## Admin User Seed

Create a script or command to generate an initial admin user:

```python
# scripts/create_admin.py or management command
async def create_admin(email: str, password: str, name: str):
    """Create admin user in the database."""
    user = User(
        name=name,
        email=email,
        password=hash_password(password),
        is_admin=True,
    )
    db.add(user)
    db.commit()
```

**Suggested environment variables for initial seed:**
```env
ADMIN_EMAIL=admin@cronosmatic.com
ADMIN_PASSWORD=<secure_password>
ADMIN_NAME=Admin CronosMatic
```

---

## Acceptance Criteria

- [ ] All admin endpoints return 403 for non-admin users
- [ ] All admin endpoints return 401 without a token
- [ ] All admin endpoints work correctly with an admin token
- [ ] Admin list endpoints show inactive items
- [ ] A script exists to create an initial admin user
- [ ] Integration tests cover all admin endpoints
