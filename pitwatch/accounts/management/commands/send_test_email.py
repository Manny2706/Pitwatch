import json
from urllib import error, request as urllib_request

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Send a test email using Brevo API"

    def add_arguments(self, parser):
        parser.add_argument("--to", required=True, help="Recipient email address")
        parser.add_argument(
            "--subject",
            default="PitWatch test email",
            help="Subject for test email",
        )

    def handle(self, *args, **options):
        recipient = options["to"]
        subject = options["subject"]

        message = (
            "This is a test email from PitWatch. "
            "If you received this, Brevo API is configured correctly."
        )

        api_key = getattr(settings, "BREVO_API_KEY", "")
        api_url = getattr(settings, "BREVO_API_URL", "https://api.brevo.com/v3/smtp/email")
        sender_email = getattr(settings, "BREVO_SENDER_EMAIL", "")
        sender_name = getattr(settings, "BREVO_SENDER_NAME", "PitWatch")

        if not api_key:
            raise CommandError("BREVO_API_KEY is not configured.")
        if not sender_email:
            raise CommandError("BREVO_SENDER_EMAIL is not configured.")

        payload = {
            "sender": {"name": sender_name, "email": sender_email},
            "to": [{"email": recipient}],
            "subject": subject,
            "textContent": message,
        }

        body = json.dumps(payload).encode("utf-8")
        req = urllib_request.Request(
            api_url,
            data=body,
            method="POST",
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "api-key": api_key,
            },
        )

        try:
            with urllib_request.urlopen(req, timeout=30) as resp:
                resp_body = resp.read().decode("utf-8") if resp.length != 0 else "{}"
                parsed = json.loads(resp_body) if resp_body else {}
        except Exception as exc:
            if isinstance(exc, error.HTTPError):
                err_body = exc.read().decode("utf-8", errors="replace")
                raise CommandError(f"Failed to send test email: HTTP {exc.code} - {err_body}") from exc
            raise CommandError(f"Failed to send test email: {exc}") from exc

        message_id = parsed.get("messageId")
        if message_id:
            self.stdout.write(self.style.SUCCESS(f"Test email sent to {recipient} (messageId: {message_id})"))
            return

        self.stdout.write(self.style.SUCCESS(f"Test email request accepted for {recipient}"))
