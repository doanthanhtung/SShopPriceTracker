import os
import tempfile
import threading
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import main
import price_history
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QCloseEvent
from PyQt5.QtCore import Qt, QTimer, QEventLoop
from PyQt5.QtTest import QTest


def response(*codes):
    return {"response": {"resultData": {"productList": [{
        "categorySubTypeEngName": "Phones",
        "modelList": [{"modelCode": code, "displayName": "Same name",
                       "price": "100", "promotionPrice": "80",
                       "priceDisplay": "80", "ctaType": "whereToBuy"}
                      for code in codes],
    }]}}}


class ProgressiveLoadingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.database_patch = patch.object(price_history, "DB_NAME", os.path.join(self.folder.name, "test.db"))
        self.database_patch.start()
        price_history.init_db()

    def tearDown(self):
        self.database_patch.stop()
        self.folder.cleanup()

    def test_fast_category_is_published_before_slow_category_completes(self):
        published = threading.Event()
        batches, errors, progress = [], [], []

        def fetch(url):
            if url == "slow":
                if not published.wait(3):
                    raise AssertionError("Fast batch was blocked by slow request")
                return response("SLOW", "FAST")
            return response("FAST", "OTHER")

        def batch_ready(batch):
            batches.append([p.modelCode for p in batch])
            published.set()

        with patch.object(main, "URL_LIST", ["slow", "fast"]), patch.object(main, "fetch_product_data", fetch):
            products = main.load_products(on_batch=batch_ready, on_error=errors.append,
                                          on_progress=lambda *args: progress.append(args))
        self.assertEqual([], errors)
        self.assertEqual(["FAST", "OTHER"], batches[0])
        self.assertEqual({"FAST", "OTHER", "SLOW"}, {p.modelCode for p in products})
        self.assertEqual(3, len(products))
        self.assertEqual((2, 2), progress[-1])

    def test_failed_category_does_not_discard_successful_results(self):
        errors = []
        with patch.object(main, "URL_LIST", ["bad", "good"]), patch.object(
            main, "fetch_product_data", side_effect=lambda url: None if url == "bad" else response("OK")
        ):
            products = main.load_products(on_error=errors.append)
        self.assertEqual(["OK"], [p.modelCode for p in products])
        self.assertEqual(1, len(errors))

    def test_worker_reports_unexpected_failure_and_still_finishes(self):
        worker = main.Worker()
        errors, done = [], []
        worker.error.connect(errors.append)
        worker.finished.connect(lambda: done.append(True))
        with patch.object(main, "load_products", side_effect=RuntimeError("database failure")):
            worker.start()
            self.assertTrue(worker.wait(3000))
            self.app.processEvents()
        self.assertEqual([True], done)
        self.assertIn("database failure", errors[0])

    def test_partial_refresh_preserves_filter_old_data_and_selection(self):
        with patch.object(main.ProductApp, "on_refresh"), patch.object(main.ProductApp, "init_tray_icon"):
            window = main.ProductApp()
        try:
            with patch.object(main, "URL_LIST", ["test"]), patch.object(main, "fetch_product_data", return_value=response("OLD")):
                old = main.load_products()[0]
            window.products = [old]
            window.update_filters()
            window.cta_filter.setCurrentText("Còn hàng")
            window.update_table()
            window.table.setCurrentIndex(window.product_model.index(0, 4))
            window.update_table()
            self.assertIs(old, window.table.currentIndex().data(Qt.UserRole))
            window._display_products = {old.modelCode: old}
            window._received_products = {}
            window.load_errors = ["network failure"]
            window.handle_product_batch([])
            window.handle_load_products_result([])
            self.assertEqual([old], window.products)
            self.assertEqual("Còn hàng", window.cta_filter.currentText())
            self.assertEqual(1, window.product_model.rowCount())
        finally:
            window.close()

    def test_refresh_does_not_start_an_overlapping_worker(self):
        with patch.object(main.ProductApp, "on_refresh"), patch.object(main.ProductApp, "init_tray_icon"):
            window = main.ProductApp()
        try:
            window._loading = True
            with patch.object(main, "Worker") as worker:
                window.on_refresh()
                worker.assert_not_called()
        finally:
            window._loading = False
            window.close()

    def test_close_requests_cancellation_without_destroying_running_worker(self):
        with patch.object(main.ProductApp, "on_refresh"), patch.object(main.ProductApp, "init_tray_icon"):
            window = main.ProductApp()
        try:
            window._loading = True
            with patch.object(main, "Worker") as worker_type, patch.object(main.QTimer, "singleShot"):
                window.worker = worker_type()
                event = QCloseEvent()
                window.closeEvent(event)
                self.assertFalse(event.isAccepted())
                self.assertTrue(window._closing)
                window.worker.requestInterruption.assert_called_once()
        finally:
            window._loading = False
            window.worker = None
            window.close()

    def test_table_actions_follow_product_after_sort_and_filter(self):
        with patch.object(main.ProductApp, "on_refresh"), patch.object(main.ProductApp, "init_tray_icon"):
            window = main.ProductApp()
        try:
            with patch.object(main, "URL_LIST", ["test"]), patch.object(main, "fetch_product_data", return_value=response("A", "B")):
                products = main.load_products()
            products[0].displayName = "First"
            products[1].displayName = "Second"
            products[1].promotionPrice = 50
            window.products = products
            window.update_table()
            self.assertEqual("B", window.product_model.products[0].modelCode)
            window.search_bar.setText("First")
            window.update_table()
            window.show()
            self.app.processEvents()
            with patch.object(window, "on_button_click") as buy, patch.object(window, "show_price_history") as history:
                for column in (4, 5):
                    index = window.product_model.index(0, column)
                    QTest.mouseClick(window.table.viewport(), Qt.LeftButton, pos=window.table.visualRect(index).center())
                buy.assert_called_once_with(products[0])
                history.assert_called_once_with("A")
            self.assertEqual([], window.table.findChildren(main.QPushButton))
        finally:
            window.close()

    def test_gui_can_filter_while_worker_is_still_loading(self):
        release = threading.Event()
        interacted = []
        loop = QEventLoop()
        with patch.object(main.price_history, "get_average_price", return_value=None):
            products = [main.Product(f"Product {i}", "", str(i), "", "/p", 100, "80", 80, "whereToBuy", "", "")
                        for i in range(2000)]

        def load(**callbacks):
            callbacks["on_batch"](products)
            release.wait(3)
            return products

        with patch.object(main, "load_products", load), patch.object(main.ProductApp, "init_tray_icon"):
            window = main.ProductApp()
            window.show()
            timer = QTimer()

            def interact():
                if window.product_model.rowCount() == 2000:
                    window.search_bar.setText("Product 1999")
                    window.update_table()
                    interacted.append((window._loading, window.product_model.rowCount()))
                    release.set()
                    timer.stop()

            timer.timeout.connect(interact)
            timer.start(20)
            window.worker.finished.connect(loop.quit)
            QTimer.singleShot(4000, loop.quit)
            try:
                loop.exec_()
                self.assertEqual([(True, 1)], interacted)
                self.assertEqual([], window.table.findChildren(main.QPushButton))
            finally:
                timer.stop()
                release.set()
                if window.worker:
                    window.worker.wait(3000)
                    self.app.processEvents()
                window.close()

    def test_email_image_is_rendered_off_gui_thread_without_pyplot(self):
        price_history.save_price_history("A", "Product", 80, "whereToBuy")
        message = "Giá sản phẩm thay đổi (Giảm dưới giá trung bình):\nGiảm giá so với giá trung bình: 20%"
        images_seen = []
        thread_ids = []

        def send(subject, body, images):
            thread_ids.append(threading.get_ident())
            for path, cid in images:
                with open(path, "rb") as image:
                    self.assertEqual(b"\x89PNG\r\n\x1a\n", image.read(8))
                images_seen.append(path)

        worker = main.EmailWorker([(message, "A")])
        with patch.object(main, "send_email", side_effect=send), patch.object(price_history.plt, "subplots", side_effect=AssertionError("GUI pyplot used by email")):
            worker.start()
            self.assertTrue(worker.wait(5000))
        self.assertEqual(1, len(images_seen))
        self.assertNotEqual(threading.get_ident(), thread_ids[0])
        self.assertFalse(os.path.exists(images_seen[0]))

    def test_worker_consumes_availability_subscription_once(self):
        price_history.subscribe_to_availability("A", "Product")
        notifications = []
        with patch.object(main, "URL_LIST", ["test"]), patch.object(main, "fetch_product_data", return_value=response("A")):
            for _ in range(2):
                main.load_products(on_notification=lambda kind, args: notifications.append(kind))
        self.assertEqual(1, notifications.count("available"))
        self.assertEqual(set(), price_history.get_availability_subscriptions())

    def test_search_by_model_code_and_clear_filters(self):
        with patch.object(main.ProductApp, "on_refresh"), patch.object(main.ProductApp, "init_tray_icon"):
            window = main.ProductApp()
        try:
            with patch.object(main, "URL_LIST", ["test"]), patch.object(main, "fetch_product_data", return_value=response("MODEL-A", "MODEL-B")):
                window.products = main.load_products()
            window.sort_filter.setCurrentIndex(1)
            window.search_bar.setText(" model-b ")
            window.update_table()
            self.assertEqual(["MODEL-B"], [p.modelCode for p in window.product_model.products])
            window.search_bar.setText("not found")
            window.update_table()
            self.assertFalse(window.empty_state.isHidden())
            window.clear_filters()
            self.assertEqual(2, window.product_model.rowCount())
            self.assertTrue(window.empty_state.isHidden())
            self.assertTrue(window.sort_filter.currentData())
        finally:
            window.close()

    def test_price_and_discount_column_match_selected_basis(self):
        with patch.object(main.ProductApp, "on_refresh"), patch.object(main.ProductApp, "init_tray_icon"):
            window = main.ProductApp()
        try:
            with patch.object(main, "URL_LIST", ["test"]), patch.object(main, "fetch_product_data", return_value=response("MODEL-A")):
                window.products = main.load_products()
            window.products[0].averagePrice = 200
            window.update_table()
            self.assertEqual("80 ₫", window.product_model.index(0, 1).data())
            self.assertEqual("20%", window.product_model.index(0, 2).data())
            window.sort_filter.setCurrentIndex(1)
            self.assertEqual("60%", window.product_model.index(0, 2).data())
            self.assertEqual("So với TB", window.product_model.headerData(2, Qt.Horizontal))
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
