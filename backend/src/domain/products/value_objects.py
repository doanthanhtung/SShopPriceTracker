from enum import StrEnum


class StoreProvider(StrEnum):
    SAMSUNG = "samsung"
    HOANG_HA = "hoang_ha"


class ProductStatus(StrEnum):
    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"
    PRE_ORDER = "pre_order"
    UNKNOWN = "unknown"

    @classmethod
    def from_samsung_cta_type(cls, cta_type: str | None) -> "ProductStatus":
        if cta_type in {"whereToBuy"}:
            return cls.IN_STOCK
        if cta_type == "preOrder":
            return cls.PRE_ORDER
        if cta_type == "outOfStock":
            return cls.OUT_OF_STOCK
        return cls.UNKNOWN

    @property
    def is_available(self) -> bool:
        return self in {self.IN_STOCK, self.PRE_ORDER}

