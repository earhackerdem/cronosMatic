# Product Requirements Document (PRD)

## Project: cronosMaticStore 

### 1. Deployment and Multimedia Architecture

* **Frontend:** Developed in React/Vite (leveraging UI components generated via v0) and hosted on Vercel.
* **Backend & Database:** FastAPI and PostgreSQL running in Docker containers, deployed on a simplified infrastructure platform (e.g., Railway, Render, or a VPS using Coolify).
* **Multimedia:** Local storage using mounted Docker volumes for the initial MVP phase, with abstractions in place for a seamless future migration to an S3-compatible cloud storage solution (e.g., Cloudflare R2) in production.

### 2. Catalog Management and Faceted Search

The system will feature independent administrative endpoints (CRUD) and a strict relational database schema to support complex combined filters in the frontend, preventing AI hallucinations:

* **Base Attributes:** SKU (Unique), Brand, Model, Reference Number, Price, Stock, Case Diameter (mm).
* **Technical Specifications (Strict Filters):**
* *Movement:* Automatic, Quartz, Hybrid, Mechanical (Manual).
* *Case Material:* Stainless Steel, Yellow Gold, Rose Gold, White Gold, Titanium, Ceramic.
* *Strap/Bracelet Material:* Leather, Steel, Gold, Rubber, NATO.
* *Water Resistance:* ATM Classification (e.g., 5, 10, 30).
* *Target Gender:* Male, Female, Unisex.
* *Style:* Daily Wear, Sport, Dress, Diver.


* **Many-to-Many Relationships:**
* *Complications:* Moon Phase, GMT, Chronograph, Tourbillon, Perpetual Calendar.
* *Occasions (Contextual Tags):* First Watch, Graduation, New Promotion, Anniversary.



### 3. User Experience: Onboarding and Access

* **Authentication:** * Native JWT-based authentication provided by the Tiangolo template.
* **Social Login:** Integration with Google OAuth 2.0 to allow frictionless, one-click registration and login.


* **Optional Onboarding:** Account creation does not force the user through a questionnaire. Upon registration, the user is redirected to their dashboard, where a non-intrusive UI component invites them to complete their profile (Age, Gender, current watch collection, or purchase intent).
* **Guest Checkout:** The purchasing flow allows unauthenticated users to buy products by providing only a contact email and shipping address during checkout.

### 4. Transaction Flow and Logistics

* **Payment Gateways:** Dual integration of Stripe (for international transactions and credit cards) and Mercado Pago (for local/regional payment methods). Webhooks will atomically process payment confirmations, deduct inventory stock, and update the order status.
* **Shipping Policy:** A global flat-rate shipping fee of $100 USD will be automatically added to the order total during checkout.

### 5. Conversational AI Engine (RAG)

* **Inference Abstraction:** An agnostic architecture using the Factory design pattern to easily swap the LLM provider (commercial APIs like Claude/OpenAI or local open-weights models).
* **Recommendation and Support Assistant:** An interactive chat interface that consumes both the user's profile data (if onboarding was completed) and the structured catalog data to offer personalized, technically accurate watch suggestions. It will also execute support functions via Tool Calling to retrieve order statuses.

---

Para comenzar con la fase de ejecución "ticket por ticket" utilizando la integración de IA local, ¿te gustaría que el **Ticket 003** se enfoque en la creación de los modelos de base de datos (SQLModel) para el catálogo de relojes, o prefieres abordar primero la configuración del Social Login con Google en el backend?