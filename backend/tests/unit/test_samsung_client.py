from decimal import Decimal

from src.domain.products import ProductStatus, StoreProvider
from src.infrastructure.scrapers.samsung_client import parse_samsung_products


def test_parse_samsung_products_maps_payload_to_domain_products() -> None:
    payload = {
        "response": {
            "resultData": {
                "productList": [
                    {
                        "categorySubTypeEngName": "Smartphones",
                        "modelList": [
                            {
                                "displayName": "Galaxy S24 Ultra",
                                "modelCode": "SM-S928",
                                "pdpUrl": "/vn/smartphones/galaxy-s24-ultra/",
                                "price": "30000000",
                                "promotionPrice": "24000000",
                                "ctaType": "whereToBuy",
                            }
                        ],
                    }
                ]
            }
        }
    }

    products = parse_samsung_products(payload)

    assert len(products) == 1
    assert products[0].provider == StoreProvider.SAMSUNG
    assert products[0].external_id == "SM-S928"
    assert products[0].name == "Galaxy S24 Ultra"
    assert products[0].status == ProductStatus.IN_STOCK
    assert products[0].product_url == "https://www.samsung.com/vn/smartphones/galaxy-s24-ultra/"
    assert products[0].original_price == Decimal("30000000")
    assert products[0].current_price == Decimal("24000000")


def test_parse_samsung_products_skips_excluded_accessory_category() -> None:
    payload = {
        "response": {
            "resultData": {
                "productList": [
                    {
                        "categorySubTypeEngName": "Washing Machines Accessories",
                        "modelList": [
                            {
                                "displayName": "Accessory",
                                "modelCode": "ACC-1",
                                "price": "100000",
                                "promotionPrice": "90000",
                                "ctaType": "whereToBuy",
                            }
                        ],
                    }
                ]
            }
        }
    }

    assert parse_samsung_products(payload) == []


def test_parse_samsung_products_ignores_models_without_required_identity() -> None:
    payload = {
        "response": {
            "resultData": {
                "productList": [
                    {
                        "categorySubTypeEngName": "Smartphones",
                        "modelList": [
                            {"displayName": "Missing code", "modelCode": ""},
                            {"displayName": "", "modelCode": "SM-S928"},
                        ],
                    }
                ]
            }
        }
    }

    assert parse_samsung_products(payload) == []

