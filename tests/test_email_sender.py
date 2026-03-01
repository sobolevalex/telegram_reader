"""Tests for EmailSender (mocked SMTP)."""

from unittest.mock import MagicMock, patch

import pytest

from telegram_reader.email_sender import EmailSender


@pytest.fixture
def sender() -> EmailSender:
    return EmailSender(
        smtp_user="user@gmail.com",
        smtp_password="pass",
        to_email="to@example.com",
    )


def test_send_digest_calls_smtp_and_send_message(sender: EmailSender) -> None:
    with (
        patch("telegram_reader.email_sender.smtplib.SMTP") as mock_smtp_class,
        patch.object(sender, "_log"),
    ):
        mock_server = MagicMock()
        mock_smtp_class.return_value = mock_server

        sender.send_digest("Hello world", "Test Subject")

        mock_smtp_class.assert_called_once()
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with(
            "user@gmail.com", "pass"
        )
        mock_server.send_message.assert_called_once()
        mock_server.quit.assert_called_once()

        # Check the message passed to send_message
        call_args = mock_server.send_message.call_args
        msg = call_args[0][0]
        assert msg["Subject"] == "Test Subject"
        assert msg["From"] == "user@gmail.com"
        assert msg["To"] == "to@example.com"
        payload = msg.get_payload(0)
        assert payload.get_payload() == "Hello world"


def test_send_digest_fallback_to_ssl_on_connection_error(
    sender: EmailSender,
) -> None:
    with (
        patch("telegram_reader.email_sender.smtplib.SMTP") as mock_smtp,
        patch("telegram_reader.email_sender.smtplib.SMTP_SSL") as mock_smtp_ssl,
        patch.object(sender, "_log"),
    ):
        mock_smtp.side_effect = OSError("Connection refused")
        mock_server = MagicMock()
        mock_smtp_ssl.return_value = mock_server

        sender.send_digest("Content", "Subject")

        mock_smtp_ssl.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.send_message.assert_called_once()
