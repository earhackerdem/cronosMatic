# Ticket 007: Frontend - Base Catalogs Admin UI (Phase 1)

## 1. Objective
Develop the administrative user interface in the React/Vite frontend to consume the backend endpoints created in Ticket 005, allowing administrators to manage the base watch catalogs.

## 2. Context
With the backend endpoints in place, the administrative dashboard requires interfaces to populate and manage the catalog data (Movement, Case Material, Target Gender, Watch Style). This data must be pre-populated before users or admins can start creating watch records in the system.

## 3. Acceptance Criteria (AC)
- [ ] **AC1:** API Client Integration. Update the frontend API client services (e.g., OpenAPI auto-generated clients or custom Axios instances) to include the endpoints for the four base catalogs.
- [ ] **AC2:** Routing & Navigation. Add protected routes in the admin dashboard section for each catalog (e.g., `/admin/catalogs/movements`, `/admin/catalogs/case-materials`, etc.) and include them in the administrative sidebar/navigation menu.
- [ ] **AC3:** Data Tables. For each catalog, implement a data table view displaying the existing records, fetching data from the `Read all` endpoints.
- [ ] **AC4:** CRUD Interfaces. Implement forms or modals triggered from the data table view to Create new records, Update existing records, and Delete records (with a confirmation dialog).
- [ ] **AC5:** UX/UI Consistency. Utilize the existing UI components and design system of the Tiangolo template (or the components previously integrated via v0) to maintain visual consistency. Include error handling toasts and loading states.

## 4. Implementation Notes
- Since the four entities are structurally identical, consider creating a reusable generic "Catalog Manager" React component that accepts the API service methods and titles as props to keep the codebase DRY (Don't Repeat Yourself).
- Ensure that form validations match the Pydantic schemas defined in the backend (e.g., required fields, string length limits).