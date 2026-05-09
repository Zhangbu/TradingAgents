import os
import unittest
from unittest.mock import patch

from backend.app.core.auth import create_session_token, verify_session_token
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
