from pydantic import BaseModel


class CreatePayPalOrderRequest(BaseModel):
    order_id: int


class CapturePayPalOrderRequest(BaseModel):
    order_id: int
    paypal_order_id: str


class SimulatePaymentRequest(BaseModel):
    order_id: int


class CreatePayPalOrderResponse(BaseModel):
    paypal_order_id: str
    approval_url: str
    order_number: str


class CapturePayPalOrderResponse(BaseModel):
    order_number: str
    payment_status: str
    capture_id: str


class SimulateSuccessResponse(BaseModel):
    order_number: str
    payment_status: str
    simulated: bool
    paypal_order_id: str
    capture_id: str


class SimulateFailureResponse(BaseModel):
    order_number: str
    payment_status: str
    simulated: bool
    paypal_order_id: str
    error: str


class VerifyConfigResponse(BaseModel):
    mode: str
    client_id_configured: bool
    client_secret_configured: bool
    simulate_payments: bool
    base_url: str
    auth_test: str
