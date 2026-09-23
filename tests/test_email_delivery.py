import base64
from email import message_from_string
from email.header import decode_header, make_header
import json
import os
import smtplib
import tempfile
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import email_delivery as delivery
import main
from PyQt5.QtTest import QSignalSpy
from PyQt5.QtCore import QEventLoop, QTimer
from PyQt5.QtWidgets import QApplication


class EmailDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.database = os.path.join(self.folder.name, "email.db")
        self.outbox = delivery.EmailOutbox(self.database)
        self.sender = "sender@example.invalid"
        self.recipients = ["a@example.invalid", "b@example.invalid", "c@example.invalid"]
        self.server = MagicMock()
        self.server.sendmail.return_value = {}

    def tearDown(self):
        self.folder.cleanup()

    def job(self, recipients=None, images=None):
        recipients = recipients or self.recipients[:1]
        msg = delivery.build_message(self.sender, recipients, "Kiểm tra", "<p>Sản phẩm</p>", images)
        self.outbox.enqueue(self.sender, recipients, msg)
        return self.outbox.jobs()[-1]

    def deliver(self, job, factory=None):
        sleep = MagicMock()
        with patch.object(delivery.smtplib, "SMTP", factory or MagicMock(return_value=self.server)):
            result = delivery.deliver_job(self.outbox, job, "smtp.example.invalid", 587,
                                          self.sender, "test-only", sleep=sleep)
        return result, sleep

    def test_success_preserves_utf8_tls_and_closes_connection(self):
        result, sleep = self.deliver(self.job())
        self.assertEqual((1, 0), (result.accepted, result.pending))
        self.assertEqual([], self.outbox.jobs())
        self.server.starttls.assert_called_once()
        self.assertIn("context", self.server.starttls.call_args.kwargs)
        self.server.login.assert_called_once_with(self.sender, "test-only")
        self.server.quit.assert_called_once()
        self.server.close.assert_called_once()
        sleep.assert_not_called()
        message = message_from_string(self.server.sendmail.call_args.args[2])
        self.assertEqual("Kiểm tra", str(make_header(decode_header(message["Subject"]))))
        self.assertIsNotNone(message["Date"])
        self.assertIsNotNone(message["Message-ID"])
        self.assertIn("Sản phẩm", message.get_payload()[0].get_payload(decode=True).decode("utf-8"))

    def test_web_login_failure_is_visible_persistent_and_not_retried(self):
        self.server.login.side_effect = smtplib.SMTPAuthenticationError(534, b"Please log in with your web browser. WebLoginRequired")
        result, sleep = self.deliver(self.job())
        self.assertEqual((0, 1), (result.accepted, result.pending))
        self.assertIn("WebLoginRequired", result.error)
        self.assertEqual(1, len(delivery.EmailOutbox(self.database).jobs()))
        self.server.sendmail.assert_not_called()
        self.server.close.assert_called_once()
        sleep.assert_not_called()

    def test_partial_refusals_retry_only_transient_recipients(self):
        self.server.sendmail.side_effect = [{self.recipients[1]: (450, b"try later"), self.recipients[2]: (550, b"rejected")}, {}]
        result, sleep = self.deliver(self.job(self.recipients))
        self.assertEqual((2, 1), (result.accepted, result.pending))
        self.assertEqual([self.recipients[1]], self.server.sendmail.call_args_list[1].args[1])
        self.assertEqual([self.recipients[2]], json.loads(self.outbox.jobs()[0]["recipients"]))
        self.assertIn("550", result.error)
        self.assertEqual(self.server.sendmail.call_args_list[0].args[2], self.server.sendmail.call_args_list[1].args[2])
        sleep.assert_called_once_with(1)

    def test_all_recipients_refused_are_not_reported_as_sent(self):
        self.server.sendmail.side_effect = smtplib.SMTPRecipientsRefused({self.recipients[0]: (550, b"No such user")})
        result, sleep = self.deliver(self.job())
        self.assertEqual((0, 1), (result.accepted, result.pending))
        self.assertIn("550", result.error)
        sleep.assert_not_called()

    def test_connection_failure_before_data_can_be_retried(self):
        factory = MagicMock(side_effect=[OSError("network"), self.server])
        result, sleep = self.deliver(self.job(), factory)
        self.assertEqual(1, result.accepted)
        self.assertEqual(2, factory.call_count)
        sleep.assert_called_once_with(1)

    def test_temporary_data_rejection_has_bounded_retries(self):
        self.server.sendmail.side_effect = smtplib.SMTPDataError(451, b"Temporary failure")
        result, sleep = self.deliver(self.job())
        self.assertEqual(3, self.server.sendmail.call_count)
        self.assertEqual([1, 2], [call.args[0] for call in sleep.call_args_list])
        self.assertEqual(1, result.pending)
        self.assertFalse(result.uncertain)

    def test_disconnect_during_data_is_not_automatically_resent(self):
        def disconnect(*args):
            self.assertEqual((1, True), self.outbox.summary())
            raise smtplib.SMTPServerDisconnected("lost acknowledgement")
        self.server.sendmail.side_effect = disconnect
        result, sleep = self.deliver(self.job())
        self.assertTrue(result.uncertain)
        self.assertEqual(1, result.pending)
        self.assertIn("trùng", result.error)
        self.server.sendmail.assert_called_once()
        sleep.assert_not_called()

    def test_quit_failure_does_not_reverse_successful_delivery(self):
        self.server.quit.side_effect = smtplib.SMTPServerDisconnected("QUIT failed")
        result, sleep = self.deliver(self.job())
        self.assertEqual((1, 0), (result.accepted, result.pending))
        self.assertEqual([], self.outbox.jobs())
        self.server.close.assert_called_once()
        sleep.assert_not_called()

    def test_failed_message_can_be_retried_after_restart(self):
        self.server.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Credentials rejected")
        job = self.job()
        self.deliver(job)
        self.server.login.side_effect = None
        with patch.object(delivery.smtplib, "SMTP", return_value=self.server):
            result = delivery.retry_queued_emails(self.database, "smtp.example.invalid", 587, self.sender, "new-password")
        self.assertEqual(1, result.accepted)
        self.assertEqual(job["message"], self.server.sendmail.call_args.args[2])
        self.assertEqual([], self.outbox.jobs())

    def test_inline_image_survives_temporary_file_cleanup(self):
        path = os.path.join(self.folder.name, "pixel.png")
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jhC8AAAAASUVORK5CYII=")
        with open(path, "wb") as file:
            file.write(png)
        job = self.job(images=[(path, "chart"), (path, "chart")])
        os.remove(path)
        self.deliver(job)
        message = message_from_string(self.server.sendmail.call_args.args[2])
        images = [part for part in message.walk() if part.get_content_maintype() == "image"]
        self.assertEqual(1, len(images))
        self.assertEqual(png, images[0].get_payload(decode=True))

    def test_duplicate_product_alerts_reuse_image_and_escape_html(self):
        message = "Giá sản phẩm thay đổi (Giảm dưới giá trung bình):\nGiảm giá so với giá trung bình: 20%\nTên: <ABC>"
        with patch.object(main, "generate_price_history_image", return_value=("chart.png", "cid")) as render:
            _, body, images = main.prepare_notification_email([(message, "A"), ("Sản phẩm có hàng với giá tốt:\nA", "A")])
        render.assert_called_once_with("A")
        self.assertEqual([("chart.png", "cid")], images)
        self.assertEqual(2, body.count('src="cid:cid"'))
        self.assertIn("&lt;ABC&gt;", body)

    def test_chart_failure_still_sends_text_content(self):
        with patch.object(main, "generate_price_history_image", side_effect=RuntimeError("chart error")):
            _, body, images = main.prepare_notification_email([("Sản phẩm có hàng với giá tốt:\nA", "A")])
        self.assertIn("Không có dữ liệu", body)
        self.assertEqual([], images)

    def test_background_worker_emits_failure_result_and_keeps_outbox(self):
        self.server.login.side_effect = smtplib.SMTPAuthenticationError(534, b"WebLoginRequired")
        with patch.object(main.price_history, "DB_NAME", self.database), patch.object(delivery.smtplib, "SMTP", return_value=self.server):
            worker = main.EmailWorker([("Sản phẩm mới:\nA", "A")])
            results = QSignalSpy(worker.result_ready)
            worker.start()
            self.assertTrue(worker.wait(4000))
            self.app.processEvents()
        self.assertEqual(1, len(results))
        self.assertIn("WebLoginRequired", results[0][0].error)
        self.assertEqual(1, len(self.outbox.jobs()))

    def test_ui_shows_failure_and_retry_resends_saved_email(self):
        def drain(window):
            loop = QEventLoop()
            timer = QTimer()
            timer.timeout.connect(lambda: loop.quit() if not window.email_workers else None)
            timer.start(10)
            timeout = QTimer()
            timeout.setSingleShot(True)
            timeout.timeout.connect(loop.quit)
            timeout.start(3000)
            loop.exec_()
            timer.stop()
            timeout.stop()
            self.assertEqual([], window.email_workers)

        self.server.login.side_effect = smtplib.SMTPAuthenticationError(534, b"WebLoginRequired")
        with patch.object(main.price_history, "DB_NAME", self.database), patch.object(delivery.smtplib, "SMTP", return_value=self.server):
            main.price_history.init_db()
            with patch.object(main.ProductApp, "on_refresh"), patch.object(main.ProductApp, "init_tray_icon"):
                window = main.ProductApp()
            try:
                self.assertTrue(window.email_controls.isHidden())
                window.notifications = [("Sản phẩm mới:\nA", "A")]
                window.load_errors = []
                window.handle_load_products_result([])
                drain(window)
                self.assertIn("WebLoginRequired", window.email_status_label.text())
                self.assertFalse(window.email_controls.isHidden())
                self.assertTrue(window.email_retry_button.isEnabled())
                self.server.login.side_effect = None
                window.retry_failed_emails()
                drain(window)
                self.assertIn("SMTP đã nhận", window.email_status_label.text())
                self.assertTrue(window.email_controls.isHidden())
                self.assertFalse(window.email_retry_button.isEnabled())
                self.assertEqual((0, False), self.outbox.summary())
                self.server.sendmail.assert_called_once()
            finally:
                window.close()


if __name__ == "__main__":
    unittest.main()
