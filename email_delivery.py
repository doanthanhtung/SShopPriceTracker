"""Durable SMTP outbox. Retry only recipients definitely not accepted by SMTP."""

from dataclasses import dataclass
from contextlib import contextmanager
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
import json
import smtplib
import sqlite3
import ssl
import time


@dataclass
class DeliveryResult:
    accepted: int = 0
    pending: int = 0
    error: str = ""
    uncertain: bool = False


class EmailOutbox:
    def __init__(self, database):
        self.database = database
        with self.connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS email_outbox (
                id TEXT PRIMARY KEY, sender TEXT NOT NULL, message TEXT NOT NULL,
                recipients TEXT NOT NULL, accepted TEXT NOT NULL DEFAULT '[]',
                error TEXT NOT NULL DEFAULT '', uncertain INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL
            )""")

    def connect(self):
        return closing_connection(self.database)

    def enqueue(self, sender, recipients, message):
        job_id = message["Message-ID"]
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO email_outbox (id, sender, message, recipients, created_at) VALUES (?, ?, ?, ?, ?)",
                (job_id, sender, message.as_string(), json.dumps(list(dict.fromkeys(recipients))), time.time()),
            )
        return job_id

    def jobs(self):
        with self.connect() as conn:
            conn.row_factory = sqlite3.Row
            return [dict(row) for row in conn.execute("SELECT * FROM email_outbox ORDER BY created_at")]

    def summary(self):
        with self.connect() as conn:
            count, uncertain = conn.execute("SELECT COUNT(*), MAX(uncertain) FROM email_outbox").fetchone()
            return count, bool(uncertain)

    def get(self, job_id):
        with self.connect() as conn:
            conn.row_factory = sqlite3.Row
            return dict(conn.execute("SELECT * FROM email_outbox WHERE id=?", (job_id,)).fetchone())

    def latest_error(self):
        with self.connect() as conn:
            row = conn.execute("SELECT error FROM email_outbox WHERE error != '' ORDER BY created_at DESC LIMIT 1").fetchone()
            return row[0] if row else ""

    def update(self, job_id, recipients, accepted, error="", uncertain=False):
        with self.connect() as conn:
            if not recipients:
                conn.execute("DELETE FROM email_outbox WHERE id = ?", (job_id,))
            else:
                conn.execute(
                    "UPDATE email_outbox SET recipients=?, accepted=?, error=?, uncertain=? WHERE id=?",
                    (json.dumps(recipients), json.dumps(accepted), error, int(uncertain), job_id),
                )


@contextmanager
def closing_connection(database):
    conn = sqlite3.connect(database, timeout=10)
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def build_message(sender, recipients, subject, body, images=None):
    if not sender or not recipients:
        raise ValueError("Chưa cấu hình địa chỉ gửi/nhận email.")
    msg = MIMEMultipart("related")
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()
    msg.attach(MIMEText(body, "html", "utf-8"))
    seen = set()
    for path, cid in images or []:
        if cid in seen:
            continue
        with open(path, "rb") as file:
            part = MIMEImage(file.read())
        part.add_header("Content-ID", f"<{cid}>")
        part.add_header("Content-Disposition", "inline")
        msg.attach(part)
        seen.add(cid)
    return msg


def smtp_error_text(exc):
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        detail = str(exc.smtp_error).lower()
        if "webloginrequired" in detail or "log in with your web browser" in detail:
            return "Google yêu cầu đăng nhập tài khoản gửi trên trình duyệt (SMTP 534 / WebLoginRequired). Xác minh rồi bấm Gửi lại email."
        return f"Đăng nhập SMTP bị từ chối ({exc.smtp_code}). Kiểm tra App Password và tài khoản Google."
    if isinstance(exc, smtplib.SMTPResponseException):
        return f"Máy chủ từ chối email (SMTP {exc.smtp_code})."
    if isinstance(exc, ssl.SSLError):
        return "Không xác minh được kết nối TLS tới máy chủ email."
    if isinstance(exc, (OSError, smtplib.SMTPServerDisconnected)):
        return "Kết nối SMTP bị ngắt hoặc hết thời gian chờ."
    return f"Không gửi được email ({type(exc).__name__})."


def smtp_attempt(host, port, user, password, sender, recipients, message, before_send):
    """Return accepted, retryable, error, uncertain; never let QUIT hide DATA success."""
    server = None
    sending = False
    try:
        if not password:
            raise ValueError("Chưa cấu hình SMTP_PASSWORD.")
        server = smtplib.SMTP(host, port, timeout=15)
        server.ehlo()
        server.starttls(context=ssl.create_default_context())
        server.ehlo()
        server.login(user, password)
        before_send()
        sending = True
        refused = server.sendmail(sender, recipients, message)
        accepted = [address for address in recipients if address not in refused]
        retryable = [address for address, (code, _) in refused.items() if 400 <= code < 500]
        codes = ", ".join(str(code) for code in sorted({value[0] for value in refused.values()}))
        error = f"SMTP từ chối {len(refused)} người nhận (mã {codes})." if refused else ""
        return accepted, retryable, error, False
    except smtplib.SMTPRecipientsRefused as exc:
        retryable = [address for address, (code, _) in exc.recipients.items() if 400 <= code < 500]
        codes = ", ".join(str(code) for code in sorted({value[0] for value in exc.recipients.values()}))
        return [], retryable, f"SMTP từ chối người nhận (mã {codes}).", False
    except smtplib.SMTPAuthenticationError as exc:
        return [], [], smtp_error_text(exc), False
    except smtplib.SMTPResponseException as exc:
        return [], list(recipients) if 400 <= exc.smtp_code < 500 else [], smtp_error_text(exc), False
    except (OSError, smtplib.SMTPServerDisconnected) as exc:
        # A disconnect during DATA may happen after delivery. Automatic retry risks duplicates.
        retryable = [] if sending or isinstance(exc, ssl.SSLError) else list(recipients)
        error = smtp_error_text(exc)
        if sending:
            error += " Chưa rõ máy chủ đã nhận thư chưa; gửi lại có thể trùng thư."
        return [], retryable, error, sending
    except Exception as exc:
        return [], [], str(exc) if isinstance(exc, ValueError) else smtp_error_text(exc), sending
    finally:
        if server is not None:
            try:
                server.quit()
            except (OSError, smtplib.SMTPException):
                pass
            finally:
                try:
                    server.close()
                except OSError:
                    pass


def deliver_job(outbox, job, host, port, user, password, max_attempts=3, sleep=time.sleep):
    pending = json.loads(job["recipients"])
    accepted = json.loads(job["accepted"])
    targets = list(pending)
    newly_accepted = 0
    errors = {}
    uncertain = False
    for attempt in range(max_attempts):
        if not targets:
            break

        def before_send():
            outbox.update(job["id"], pending, accepted, "Chưa có xác nhận SMTP; gửi lại có thể trùng thư.", True)

        delivered, retryable, error, unknown = smtp_attempt(
            host, port, user, password, job["sender"], targets, job["message"], before_send,
        )
        uncertain = uncertain or unknown
        for address in targets:
            if address in delivered:
                pending.remove(address)
                accepted.append(address)
                newly_accepted += 1
                errors.pop(address, None)
            else:
                errors[address] = error
        detail = " ".join(dict.fromkeys(errors.values()))
        outbox.update(job["id"], pending, accepted, detail, uncertain)
        targets = retryable
        if targets and attempt + 1 < max_attempts:
            sleep(2 ** attempt)
    return DeliveryResult(newly_accepted, len(pending), " ".join(dict.fromkeys(errors.values())), uncertain)


def send_queued_email(database, host, port, user, password, recipients, subject, body, images=None):
    outbox = EmailOutbox(database)
    message = build_message(user, recipients, subject, body, images)
    job_id = outbox.enqueue(user, recipients, message)
    job = outbox.get(job_id)
    return deliver_job(outbox, job, host, port, user, password)


def retry_queued_emails(database, host, port, user, password):
    outbox = EmailOutbox(database)
    result = DeliveryResult()
    for job in outbox.jobs():
        delivered = deliver_job(outbox, job, host, port, user, password)
        result.accepted += delivered.accepted
        result.pending += delivered.pending
        result.uncertain = result.uncertain or delivered.uncertain
        if delivered.error:
            result.error = delivered.error
    return result
