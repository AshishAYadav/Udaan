from fastapi import APIRouter, Header

from app.schemas.misc import Currency, CurrencyDetection
from app.services import currency_service

router = APIRouter(prefix="/currencies", tags=["Currencies"])


@router.get("", response_model=list[Currency], summary="Supported currencies",
            description="Point-of-sale currencies with sandbox reference rates (units per 1 USD).")
def list_currencies():
    return currency_service.list_currencies()


@router.get("/detect", response_model=CurrencyDetection, summary="Suggest a currency for the caller",
            description="Uses a CDN geo-IP header (`CF-IPCountry`, `X-Country-Code`) when present, otherwise the region "
                        "in `Accept-Language` (e.g. en-IN → INR). Falls back to USD.")
def detect(
    cf_ipcountry: str | None = Header(None),
    x_country_code: str | None = Header(None),
    accept_language: str | None = Header(None),
):
    return currency_service.detect(cf_ipcountry or x_country_code, accept_language)
