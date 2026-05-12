import os
import unittest
from unittest.mock import patch

from backend.app.core.auth import create_session_token, verify_session_token
from backend.app.core.auth import (
    clear_failed_logins,
    get_login_client_key,
    is_login_rate_limited,
    register_failed_login,
)
from backend.app.core.config import Settings


class PlatformAuthTests(unittest.TestCase):
    def test_session_token_round_trip(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TRADINGAGENTS_AUTH_ENABLED": "true",
                "TRADINGAGENTS_AUTH_USERNAME": "operator",
                "TRADINGAGENTS_AUTH_PASSWORD": "secret-password",
                "TRADINGAGENTS_AUTH_SECRET": "very-secret-key",
                "TRADINGAGENTS_AUTH_SESSION_TTL_HOURS": "24",
            },
            clear=False,
        ):
            settings = Settings()
            token = create_session_token("operator", settings)

        self.assertEqual(verify_session_token(token, settings), "operator")

    def test_invalid_signature_returns_none(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TRADINGAGENTS_AUTH_ENABLED": "true",
                "TRADINGAGENTS_AUTH_SECRET": "very-secret-key",
            },
            clear=False,
        ):
            settings = Settings()
            token = create_session_token("operator", settings)

        tampered = f"{token}tampered"
        self.assertIsNone(verify_session_token(tampered, settings))

    def test_rate_limit_blocks_after_max_attempts(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TRADINGAGENTS_AUTH_ENABLED": "true",
                "TRADINGAGENTS_AUTH_SECRET": "very-secret-key",
                "TRADINGAGENTS_AUTH_MAX_LOGIN_ATTEMPTS": "2",
                "TRADINGAGENTS_AUTH_LOGIN_WINDOW_MINUTES": "15",
            },
            clear=False,
        ):
            settings = Settings()
            client_key = "127.0.0.1"
            clear_failed_logins(client_key)
            register_failed_login(client_key, settings)
            self.assertFalse(is_login_rate_limited(client_key, settings))
            register_failed_login(client_key, settings)
            self.assertTrue(is_login_rate_limited(client_key, settings))
            clear_failed_logins(client_key)
