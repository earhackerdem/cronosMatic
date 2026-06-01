## 1. Database Models and Schemas

- [x] 1.1 Add `MovementBase`, `MovementCreate`, `MovementUpdate`, `Movement` (table=True), and `MovementPublic` / `MovementsPublic` classes to `backend/app/models.py`
- [x] 1.2 Add `CaseMaterialBase`, `CaseMaterialCreate`, `CaseMaterialUpdate`, `CaseMaterial` (table=True), and `CaseMaterialPublic` / `CaseMaterialsPublic` classes to `backend/app/models.py`
- [x] 1.3 Add `TargetGenderBase`, `TargetGenderCreate`, `TargetGenderUpdate`, `TargetGender` (table=True), and `TargetGenderPublic` / `TargetGendersPublic` classes to `backend/app/models.py`
- [x] 1.4 Add `WatchStyleBase`, `WatchStyleCreate`, `WatchStyleUpdate`, `WatchStyle` (table=True), and `WatchStylePublic` / `WatchStylesPublic` classes to `backend/app/models.py`

## 2. Alembic Migration

- [ ] 2.1 Inside the backend container, run `alembic revision --autogenerate -m "add catalog tables"` and confirm all four tables appear in the generated migration
- [ ] 2.2 Apply migration with `alembic upgrade head` and verify the four tables exist in `app_test_db` (and dev DB)

## 3. CRUD Router

- [x] 3.1 Create `backend/app/api/routes/catalogs.py` with a factory helper that generates five endpoints (POST, GET /, GET /{id}, PUT /{id}, DELETE /{id}) for a given catalog entity, all guarded by `get_current_active_superuser`
- [x] 3.2 Instantiate four sub-routers using the factory for Movement (`/movements`), CaseMaterial (`/case-materials`), TargetGender (`/target-genders`), WatchStyle (`/watch-styles`) and combine them under a single `router` with prefix `/catalogs`
- [x] 3.3 Wrap the DELETE handler in a try/except for `sqlalchemy.exc.IntegrityError` and raise HTTP 409 Conflict

## 4. Router Registration

- [x] 4.1 Import `catalogs` router in `backend/app/api/main.py` and add `api_router.include_router(catalogs.router)`

## 5. Tests

- [x] 5.1 Create `backend/tests/api/routes/test_catalogs.py` with fixtures that create catalog entries for each entity type
- [x] 5.2 Write `test_create_<entity>` tests (one per entity) asserting HTTP 200, correct `id` and `name` in response
- [x] 5.3 Write `test_read_<entity>s` list tests asserting HTTP 200, `data` array and `count` fields
- [x] 5.4 Write `test_read_<entity>` single-item tests asserting HTTP 200 with correct fields
- [x] 5.5 Write `test_read_<entity>_not_found` tests asserting HTTP 404
- [x] 5.6 Write `test_update_<entity>` tests asserting HTTP 200 with updated fields
- [x] 5.7 Write `test_update_<entity>_not_found` tests asserting HTTP 404
- [x] 5.8 Write `test_delete_<entity>` tests asserting HTTP 200 and entry removed
- [x] 5.9 Write `test_delete_<entity>_not_found` tests asserting HTTP 404
- [x] 5.10 Write `test_create_<entity>_forbidden` tests using `normal_user_token_headers` asserting HTTP 403 (one per entity is sufficient)
- [ ] 5.11 Run `docker compose exec backend pytest backend/tests/api/routes/test_catalogs.py -v` and confirm all tests pass
