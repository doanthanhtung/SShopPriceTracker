from collections.abc import Iterable
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.core.errors import ExternalServiceError
from src.domain.products import Product, ProductStatus, StoreProvider

SAMSUNG_PRODUCT_URLS: tuple[str, ...] = (
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=01010000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=01020000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=01030000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=04010000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=08030000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=08010000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=07010000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=08050000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=08080000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=08040000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=08070000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=09010000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=01040000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
)

EXCLUDED_SAMSUNG_CATEGORIES = frozenset({"Washing Machines Accessories"})
SAMSUNG_BASE_URL = "https://www.samsung.com"


class SamsungProductClient:
    def __init__(
        self,
        http_client: httpx.AsyncClient,
        urls: Iterable[str] = SAMSUNG_PRODUCT_URLS,
    ) -> None:
        self._http_client = http_client
        self._urls = tuple(urls)

    async def fetch_products(self) -> list[Product]:
        products_by_external_id: dict[str, Product] = {}
        for url in self._urls:
            payload = await self._fetch_json(url)
            for product in parse_samsung_products(payload):
                products_by_external_id[product.external_id] = product

        return sorted(
            products_by_external_id.values(),
            key=lambda product: (
                -product.discount_percentage(),
                product.current_price or Decimal("0"),
                not product.is_available,
            ),
        )

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, ExternalServiceError)),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def _fetch_json(self, url: str) -> dict[str, Any]:
        try:
            response = await self._http_client.get(url)
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError:
            raise
        except ValueError as exc:
            raise ExternalServiceError("Samsung API returned invalid JSON.") from exc

        if not isinstance(payload, dict):
            raise ExternalServiceError("Samsung API returned an unexpected payload shape.")
        return payload


def parse_samsung_products(payload: dict[str, Any]) -> list[Product]:
    product_list = (
        payload.get("response", {})
        .get("resultData", {})
        .get("productList", [])
    )
    if not isinstance(product_list, list):
        raise ExternalServiceError("Samsung product list is missing or invalid.")

    products: list[Product] = []
    for raw_product in product_list:
        if not isinstance(raw_product, dict):
            continue

        category = _as_text(raw_product.get("categorySubTypeEngName"))
        if category in EXCLUDED_SAMSUNG_CATEGORIES:
            continue

        model_list = raw_product.get("modelList", [])
        if not isinstance(model_list, list):
            continue

        for raw_model in model_list:
            if not isinstance(raw_model, dict):
                continue
            parsed = _parse_samsung_model(raw_model, category)
            if parsed is not None:
                products.append(parsed)

    return products


def _parse_samsung_model(raw_model: dict[str, Any], category: str | None) -> Product | None:
    model_code = _as_text(raw_model.get("modelCode"))
    display_name = _as_text(raw_model.get("displayName"))
    if not model_code or not display_name:
        return None

    pdp_url = _as_text(raw_model.get("pdpUrl")) or _as_text(raw_model.get("originPdpUrl"))
    return Product(
        provider=StoreProvider.SAMSUNG,
        external_id=model_code,
        name=display_name,
        status=ProductStatus.from_samsung_cta_type(_as_text(raw_model.get("ctaType"))),
        product_url=_normalize_samsung_url(pdp_url),
        category=category,
        original_price=_to_decimal(raw_model.get("price")),
        current_price=_to_decimal(raw_model.get("promotionPrice")),
    )


def _normalize_samsung_url(path_or_url: str | None) -> str | None:
    if not path_or_url:
        return None
    if path_or_url.startswith(("http://", "https://")):
        return path_or_url
    if path_or_url.startswith("/"):
        return f"{SAMSUNG_BASE_URL}{path_or_url}"
    return f"{SAMSUNG_BASE_URL}/{path_or_url}"


def _to_decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
