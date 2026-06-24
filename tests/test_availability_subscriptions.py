import os
import tempfile
import unittest

import price_history
from main import Product, sort_products


class AvailabilitySubscriptionTests(unittest.TestCase):
    def setUp(self):
        self.database = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.database.close()
        self.original_database = price_history.DB_NAME
        price_history.DB_NAME = self.database.name
        price_history.init_db()

    def tearDown(self):
        price_history.DB_NAME = self.original_database
        os.unlink(self.database.name)

    def test_subscription_is_persistent_and_unique_per_product(self):
        price_history.subscribe_to_availability("MODEL-1", "Tên cũ")
        price_history.subscribe_to_availability("MODEL-1", "Tên mới")

        self.assertEqual({"MODEL-1"}, price_history.get_availability_subscriptions())

    def test_consuming_subscription_prevents_duplicate_notifications(self):
        price_history.subscribe_to_availability("MODEL-1", "Sản phẩm")

        self.assertTrue(price_history.consume_availability_subscription("MODEL-1"))
        self.assertFalse(price_history.consume_availability_subscription("MODEL-1"))
        self.assertEqual(set(), price_history.get_availability_subscriptions())

    def test_unsubscribe_removes_subscription(self):
        price_history.subscribe_to_availability("MODEL-1", "Sản phẩm")
        price_history.unsubscribe_from_availability("MODEL-1")

        self.assertEqual(set(), price_history.get_availability_subscriptions())

    def test_sort_by_average_discount_uses_historical_price(self):
        price_history.save_price_history("MODEL-A", "A", 1_000_000, "whereToBuy")
        price_history.save_price_history("MODEL-B", "B", 1_000_000, "whereToBuy")
        product_a = self.make_product("MODEL-A", 700_000)
        product_b = self.make_product("MODEL-B", 800_000)

        self.assertEqual(
            ["MODEL-A", "MODEL-B"],
            [product.modelCode for product in sort_products([product_b, product_a], True)],
        )

    def test_product_without_history_has_no_average_discount(self):
        product = self.make_product("NO-HISTORY", 500_000)

        self.assertEqual(0, product.get_discount_from_average())

    @staticmethod
    def make_product(model_code, promotion_price):
        return Product(
            "Sản phẩm",
            "",
            model_code,
            "",
            "/product",
            1_000_000,
            "1.000.000₫",
            promotion_price,
            "whereToBuy",
            "",
            "Danh mục",
        )


if __name__ == "__main__":
    unittest.main()
