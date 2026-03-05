# Ticket 01: Authentication (JWT)

**Priority:** P0 — Blocker for tickets 04-09  
**Dependencies:** Ticket 00  
**Estimate:** 1 session

---

## Objective

Implement JWT authentication (access + refresh token), including registration, login, logout, refresh, and retrieving the authenticated user.

---

## Model: User

```
Table: users

| Field              | Type         | Constraints                    |
|--------------------|--------------|-------------------------------|
| id                 | Integer      | PK, autoincrement              |
| name               | String(255)  | NOT NULL                       |
| email              | String(255)  | NOT NULL, UNIQUE               |
| password           | String(255)  | NOT NULL (hashed with bcrypt)  |
| is_admin           | Boolean      | NOT NULL, DEFAULT false        |
| email_verified_at  | DateTime     | NULLABLE                       |
| created_at         | DateTime     | NOT NULL, DEFAULT now()        |
| updated_at         | DateTime     | NOT NULL, DEFAULT now(), ON UPDATE now() |
```

---

## Endpoints

### POST /api/v1/auth/register

**Auth:** public  
**Request body:**
```json
{
  "name": "string (required)",
  "email": "string (required, valid email, unique)",
  "password": "string (required, min 8 chars)",
  "password_confirmation": "string (required, must match password)"
}
```

**Response 201:**
```json
{
  "data": {
    "user": {
      "id": 1,
      "name": "Juan Pérez",
      "email": "juan@example.com",
      "created_at": "2026-03-05T12:00:00Z",
      "updated_at": "2026-03-05T12:00:00Z"
    },
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer"
  }
}
```

**Errors:**
- 422: duplicate email, validation failed

---

### POST /api/v1/auth/login

**Auth:** public  
**Request body:**
```json
{
  "email": "string (required)",
  "password": "string (required)"
}
```

**Response 200:**
```json
{
  "data": {
    "user": {
      "id": 1,
      "name": "Juan Pérez",
      "email": "juan@example.com",
      "is_admin": false,
      "created_at": "2026-03-05T12:00:00Z",
      "updated_at": "2026-03-05T12:00:00Z"
    },
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer"
  }
}
```

**Errors:**
- 422: incorrect credentials. Return error on the `email` field with message: `"The provided credentials are incorrect."`

---

### POST /api/v1/auth/refresh

**Auth:** public (receives refresh token in body, not in header)  
**Request body:**
```json
{
  "refresh_token": "string (required)"
}
```

**Response 200:**
```json
{
  "data": {
    "access_token": "eyJ...",
    "token_type": "bearer"
  }
}
```

**Errors:**
- 401: invalid or expired refresh token

---

### POST /api/v1/auth/logout

**Auth:** Bearer token (access token)  
**Response:** 204 No Content

**Behavior:** Invalidate the user's refresh token. The access token will simply expire on its own.

---

### GET /api/v1/auth/user

**Auth:** Bearer token  
**Response 200:**
```json
{
  "data": {
    "id": 1,
    "name": "Juan Pérez",
    "email": "juan@example.com",
    "is_admin": false,
    "created_at": "2026-03-05T12:00:00Z",
    "updated_at": "2026-03-05T12:00:00Z"
  }
}
```

**Errors:**
- 401: invalid or expired token

---

### GET /api/v1/auth-status

**Auth:** Bearer token  
**Response 200:**
```json
{
  "status": "ok",
  "message": "Authentication is working",
  "user": {
    "id": 1,
    "name": "Juan Pérez",
    "email": "juan@example.com",
    "is_admin": false
  },
  "timestamp": "2026-03-05T12:00:00Z"
}
```

---

## JWT Specifications

| Parameter | Value |
|-----------|-------|
| Algorithm | HS256 |
| Access token payload | `{ "sub": user_id, "email": email, "is_admin": bool, "exp": timestamp, "type": "access" }` |
| Access token TTL | 30 minutes (configurable via env) |
| Refresh token payload | `{ "sub": user_id, "exp": timestamp, "type": "refresh" }` |
| Refresh token TTL | 7 days (configurable via env) |
| Password hashing | bcrypt via passlib |

---

## Dependency: get_current_user

Create a reusable FastAPI Dependency:
- Extracts the Bearer token from the `Authorization` header.
- Decodes the JWT, verifies `type == "access"` and that it is not expired.
- Looks up the user in the DB by `sub` (user_id).
- If the user does not exist or the token is invalid, returns 401.
- Returns the User object.

## Dependency: get_current_user_optional

Same as `get_current_user` but returns `None` if no token is present (instead of 401). Used in endpoints that support both authenticated and guest users.

## Dependency: require_admin

Uses `get_current_user`, verifies that `user.is_admin == True`. If not, returns 403 with `{ "message": "Forbidden. User is not an administrator." }`.

---

## Acceptance Criteria

- [ ] Registration creates a user with a hashed password in the DB
- [ ] Registration returns access + refresh token
- [ ] Login with correct credentials returns tokens
- [ ] Login with incorrect credentials returns 422
- [ ] Registration with a duplicate email returns 422
- [ ] `GET /auth/user` with a valid token returns user data
- [ ] `GET /auth/user` without a token returns 401
- [ ] `POST /auth/refresh` with a valid refresh token returns a new access token
- [ ] `POST /auth/refresh` with an expired refresh token returns 401
- [ ] `POST /auth/logout` returns 204
- [ ] Access token expires after the configured TTL
- [ ] `is_admin` is false by default on registration
- [ ] Dependency `require_admin` returns 403 for non-admin users
