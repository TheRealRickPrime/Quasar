from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.config import settings
from app.models.esim import ESimOrder, ESimOrderRequest, ESimPlan, ESimProvider, ESimUsage, ESimWebhookEvent
from app.security import get_current_user

router = APIRouter(prefix="/esim", tags=["esim"])


PROVIDER_CATALOG: list[ESimProvider] = [
    ESimProvider(
        id="airalo",
        name="Airalo",
        display_name="Airalo",
        description="Popular travel eSIM marketplace with instant digital activation and broad regional coverage.",
        api_base_url=settings.airalo_api_url,
        coverage_countries=["US", "CA", "GB", "FR", "JP", "KR", "AU", "SG", "AE"],
    ),
    ESimProvider(
        id="esim-access",
        name="eSIM Access",
        display_name="eSIM Access",
        description="Global data plans and partner reseller platform optimized for travelers and remote workers.",
        api_base_url=settings.esim_access_api_url,
        coverage_countries=["US", "DE", "FR", "ES", "IT", "JP", "IN", "TH", "BR"],
    ),
]


PLAN_CATALOG: list[ESimPlan] = [
    ESimPlan(
        id="airalo-1gb-7d",
        provider="airalo",
        provider_name="Airalo",
        country_code="US",
        destination="United States",
        name="USA 1GB",
        data_gb=1,
        validity_days=7,
        price_cents=550,
        description="Quick 1GB plan for short trips and limited browsing.",
        instant_activation=True,
    ),
    ESimPlan(
        id="airalo-3gb-15d",
        provider="airalo",
        provider_name="Airalo",
        country_code="JP",
        destination="Japan",
        name="Japan 3GB",
        data_gb=3,
        validity_days=15,
        price_cents=1250,
        description="Reliable entry-level plan for regional travel, maps, and messaging.",
        instant_activation=True,
    ),
    ESimPlan(
        id="airalo-5gb-30d",
        provider="airalo",
        provider_name="Airalo",
        country_code="EU",
        destination="Europe",
        name="Europe 5GB",
        data_gb=5,
        validity_days=30,
        price_cents=2200,
        description="Portable regional data for business travel and tourism.",
        instant_activation=True,
    ),
    ESimPlan(
        id="esim-access-2gb-7d",
        provider="esim-access",
        provider_name="eSIM Access",
        country_code="SG",
        destination="Singapore",
        name="Singapore 2GB",
        data_gb=2,
        validity_days=7,
        price_cents=650,
        description="Ideal for short stopovers and immediate connectivity on arrival.",
        instant_activation=True,
    ),
    ESimPlan(
        id="esim-access-10gb-30d",
        provider="esim-access",
        provider_name="eSIM Access",
        country_code="AE",
        destination="UAE",
        name="UAE 10GB",
        data_gb=10,
        validity_days=30,
        price_cents=2900,
        description="Large-capacity plan for remote work and streaming while abroad.",
        instant_activation=True,
    ),
]


ORDER_STORE: dict[str, ESimOrder] = {}
USAGE_STORE: dict[str, ESimUsage] = {}


def _provider_for(provider_name: str) -> ESimProvider:
    provider = next((item for item in PROVIDER_CATALOG if item.id.lower() == provider_name.lower()), None)
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown eSIM provider: {provider_name}")
    return provider


def _plan_for(provider_name: str, plan_id: str) -> ESimPlan:
    plan = next(
        (item for item in PLAN_CATALOG if item.provider.lower() == provider_name.lower() and item.id.lower() == plan_id.lower()),
        None,
    )
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown eSIM plan: {plan_id}")
    return plan


def _customer_price(plan: ESimPlan, plan_id: str) -> int:
    if plan_id == "free":
        return 0
    if plan.price_cents <= 0:
        return 0
    return int(plan.price_cents * (1 + settings.esim_margin_percent_standard))


@router.get("/providers", response_model=list[ESimProvider])
async def get_providers():
    return PROVIDER_CATALOG


@router.get("/plans", response_model=list[ESimPlan])
async def get_plans(provider: str | None = None, destination: str | None = None):
    plans = PLAN_CATALOG
    if provider:
        plans = [item for item in plans if item.provider.lower() == provider.lower()]
    if destination:
        plans = [item for item in plans if destination.lower() in item.destination.lower() or destination.lower() in item.country_code.lower()]
    return plans


@router.post("/orders", response_model=ESimOrder, status_code=status.HTTP_201_CREATED)
async def create_esim_order(payload: ESimOrderRequest, current_user: dict[str, Any] = Depends(get_current_user)):
    provider = _provider_for(payload.provider)
    plan = _plan_for(payload.provider, payload.plan_id)

    order = ESimOrder(
        user_id=current_user["id"],
        provider=provider.id,
        plan_id=plan.id,
        destination=payload.destination or plan.destination,
        status="queued",
        qr_code_data=f"quasar://esim/{provider.id}/{plan.id}?country={payload.country_code or plan.country_code}",
        activation_code=f"{provider.id.upper()}-{plan.id.upper()}-{datetime.utcnow().strftime('%d%H%M%S')}",
        price_cents=plan.price_cents,
        paid_cents=_customer_price(plan, current_user.get("plan_id", "free")),
        expires_at=datetime.utcnow() + timedelta(days=max(1, plan.validity_days)),
    )
    ORDER_STORE[order.id] = order
    USAGE_STORE[order.id] = ESimUsage(
        order_id=order.id,
        provider=provider.id,
        country_code=payload.country_code or plan.country_code,
        data_total_mb=plan.data_gb * 1024,
        usage_percent=0.0,
    )
    return order


@router.get("/orders/{order_id}", response_model=ESimOrder)
async def get_esim_order(order_id: str, current_user: dict[str, Any] = Depends(get_current_user)):
    order = ORDER_STORE.get(order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="eSIM order not found")
    if order.user_id != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view this order")
    return order


@router.get("/orders/{order_id}/usage", response_model=ESimUsage)
async def get_esim_usage(order_id: str, current_user: dict[str, Any] = Depends(get_current_user)):
    order = ORDER_STORE.get(order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="eSIM order not found")
    if order.user_id != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view this order usage")
    usage = USAGE_STORE.get(order_id)
    if usage is None:
        plan = _plan_for(order.provider, order.plan_id)
        usage = ESimUsage(
            order_id=order.id,
            provider=order.provider,
            country_code=plan.country_code,
            data_total_mb=plan.data_gb * 1024,
            data_used_mb=0,
            usage_percent=0.0,
        )
        USAGE_STORE[order.id] = usage
    return usage


@router.post("/webhook")
async def esim_webhook(event: ESimWebhookEvent):
    order = ORDER_STORE.get(event.order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="eSIM order not found")

    if event.status:
        order.status = event.status
    if event.usage_percent is not None:
        usage = USAGE_STORE.setdefault(
            order.id,
            ESimUsage(order_id=order.id, provider=order.provider, country_code=order.destination[:2].upper()),
        )
        usage.usage_percent = max(0.0, min(100.0, float(event.usage_percent)))
        usage.data_used_mb = int((usage.usage_percent / 100.0) * usage.data_total_mb)
    order.updated_at = datetime.utcnow()
    return {"accepted": True, "order_id": order.id, "status": order.status}


@router.get("/plans/{provider_id}", response_model=list[ESimPlan])
async def get_provider_plans(provider_id: str):
    return [item for item in PLAN_CATALOG if item.provider.lower() == provider_id.lower()]
