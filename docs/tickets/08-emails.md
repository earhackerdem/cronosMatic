# Ticket 08: Emails (Celery + Redis)

**Priority:** P2  
**Dependencies:** Ticket 00, Ticket 06 (Order)  
**Estimate:** 1 session

---

## Objective

Configure Celery with Redis as broker for asynchronous email delivery. Implement the order confirmation email that is sent when payment is successful.

---

## Infrastructure

### Celery config

```python
# app/celery_app.py
from celery import Celery
from celery.schedules import crontab

celery_app = Celery(
    "cronosmatic",
    broker="redis://localhost:6379/0",  # from env var REDIS_URL
    backend="redis://localhost:6379/0",
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Mexico_City",
    enable_utc=True,
    task_default_retry_delay=60,  # 60 seconds between retries
    task_max_retries=3,
)

# Celery Beat Schedule required for cron jobs
celery_app.conf.beat_schedule = {
    "cancel-abandoned-orders-every-15-mins": {
        "task": "app.tasks.order_tasks.cancel_abandoned_orders",
        "schedule": crontab(minute="*/15"),
    },
}
```

### Worker and Beat commands

```bash
# Run the worker to process tasks
celery -A app.celery_app worker --loglevel=info

# Run beat to schedule cron tasks (in a separate terminal)
celery -A app.celery_app beat --loglevel=info
```

---

## Order Confirmation Email

### When It Is Sent

It is enqueued when `OrderService.update_payment_status()` receives `payment_status = 'paid'`.

### Recipient

- If the order has a `user_id` → user's email (`user.email`).
- If the order is from a guest → `guest_email`.
- If no email is available → DO NOT send (skip silently).

### Email Content

| Field | Value |
|-------|-------|
| From | `MAIL_FROM` env var (e.g.: `noreply@cronosmatic.com`) |
| Subject | `Order Confirmation #{order_number}` |
| Body | HTML template with order details |

**Template must include:**
- Order number (`order_number`)
- List of items (name, quantity, unit price, subtotal)
- Subtotal, shipping cost, total
- Shipping address
- URL to view the order (link to the React frontend)

---

## Background Tasks

### Order Maintenance

```python
# app/tasks/order_tasks.py
import asyncio

@celery_app.task
def cancel_abandoned_orders():
    """
    Finds orders stuck in 'pending_payment' for more than 30 minutes
    and cancels them, which automatically releases their reserved stock.
    Runs periodically via Celery Beat.
    """
    # 1. Query orders where status == PENDING_PAYMENT and created_at < now() - 30 minutes
    # 2. For each order, execute the async cancel_order service using asyncio.run
    # asyncio.run(OrderService.cancel_order(order, reason="Abandoned checkout"))
```

### Email Task

```python
# app/tasks/email_tasks.py
import asyncio

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_order_confirmation_email(self, order_id: int):
    """
    Sends order confirmation email.
    Runs asynchronously via Celery worker.
    Retries up to 3 times on failure.
    """
    # 1. Fetch order from DB (using a sync DB engine or wrapping async fetch with asyncio.run)
    # 2. Determine recipient email
    # 3. Render HTML template
    # 4. Send via SMTP/SES
    # 5. If fails, retry with exponential backoff
```

### Integration with OrderService

```python
# In OrderService.update_payment_status():
async def update_payment_status(
    self, db: AsyncSession, order, payment_status, payment_id, payment_gateway
):
    order.payment_status = payment_status
    order.payment_id = payment_id
    order.payment_gateway = payment_gateway

    if payment_status == PaymentStatus.PAID and order.status == OrderStatus.PENDING_PAYMENT:
        order.status = OrderStatus.PROCESSING

    await db.commit()

    # Enqueue email if paid (Celery task — sync call, non-blocking)
    if payment_status == PaymentStatus.PAID:
        send_order_confirmation_email.delay(order.id)

    return order
```

---

## Email Configuration

| Environment Variable | Description |
|---------------------|-------------|
| `MAIL_FROM` | Sender email |
| `MAIL_FROM_NAME` | Sender name (e.g.: "CronosMatic") |
| `MAIL_SERVER` | SMTP server host |
| `MAIL_PORT` | SMTP port (587 for TLS) |
| `MAIL_USERNAME` | SMTP username |
| `MAIL_PASSWORD` | SMTP password |
| `MAIL_TLS` | `true` for TLS |
| `MAIL_SSL` | `false` (or `true` if using SSL) |

**Note:** If using AWS SES, configure via SMTP or via `boto3` SES SDK.

---

## Acceptance Criteria

- [ ] Celery worker starts and connects to Redis
- [ ] Celery Beat is configured and runs without errors
- [ ] Abandoned orders task cancels orders older than 30 mins
- [ ] When payment is marked as `paid`, an email task is enqueued
- [ ] Email is sent to the user's email (authenticated order)
- [ ] Email is sent to `guest_email` (guest order)
- [ ] No email is sent if no email is available
- [ ] No email is sent if payment_status is not `paid`
- [ ] Email contains: order_number, items, totals, shipping address
- [ ] Subject includes the order_number
- [ ] Send failures are retried up to 3 times
- [ ] Email delivery does not block the HTTP response (it is asynchronous)
