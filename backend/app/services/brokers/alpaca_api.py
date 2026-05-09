from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.app.schemas.broker import AlpacaBrokerConfig
from backend.app.schemas.order import AccountSnapshot, BrokerEnvironment, BrokerName, OrderRecord, OrderStatus, OrderType, PositionRecord


class AlpacaApiPaperBrokerAdapter:
    """Broker adapter that talks to Alpaca's paper trading REST API."""

    def __init__(
        self,
        config: AlpacaBrokerConfig,
        session: Any | None = None,
    ) -> None:
        if not config.api_key or not config.secret_key:
            raise ValueError("Alpaca API credentials are required for API mode.")

        self.config = config
        self.session = session or self._build_default_session()
        self.base_url = config.base_url.rstrip("/")

    def submit_order(self, order: OrderRecord) -> OrderRecord:
        payload: dict[str, Any] = {
            "symbol": order.symbol,
            "qty": str(order.quantity),
            "side": order.side,
            "type": order.order_type.value,
            "time_in_force": "day",
            "client_order_id": order.id,
        }
        if order.order_type == OrderType.limit and order.requested_price is not None:
            payload["limit_price"] = str(order.requested_price)

        remote = self._extract_json(self._request("POST", "/orders", json=payload)) or {}
        return self._merge_remote_order(order, remote)

    def get_account_snapshot(self) -> AccountSnapshot:
        account = self._request("GET", "/account").json()
        positions = self._request("GET", "/positions").json()
        return AccountSnapshot(
            cash=float(account.get("cash", 0.0)),
            equity=float(account.get("equity", 0.0)),
            buying_power=float(account.get("buying_power", 0.0)),
            positions=[
                PositionRecord(
                    symbol=item["symbol"],
                    quantity=int(float(item.get("qty", 0))),
                    average_price=float(item.get("avg_entry_price", 0.0)),
                    market_value=float(item.get("market_value", 0.0)),
                )
                for item in positions
            ],
        )

    def sync_order(self, order: OrderRecord) -> OrderRecord:
        if not order.broker_order_id:
            return order

        remote = self._extract_json(self._request("GET", f"/orders/{order.broker_order_id}")) or {}
        return self._merge_remote_order(order, remote)

    def _request(self, method: str, path: str, **kwargs):
        headers = {
            "APCA-API-KEY-ID": self.config.api_key or "",
            "APCA-API-SECRET-KEY": self.config.secret_key or "",
        }
        try:
            response = self.session.request(
                method=method,
                url=f"{self.base_url}{path}",
                headers=headers,
                timeout=15,
                **kwargs,
            )
        except Exception as exc:
            raise ValueError(self._format_transport_error(path, exc)) from exc

        try:
            response.raise_for_status()
        except Exception as exc:
            raise ValueError(self._format_http_error(path, response, exc)) from exc
        return response

    def _merge_remote_order(self, order: OrderRecord, remote: dict[str, Any]) -> OrderRecord:
        remote_status = str(remote.get("status", "")).lower()
        order.broker_order_id = remote.get("id") or order.broker_order_id
        order.last_synced_at = datetime.now(timezone.utc)
        order.updated_at = datetime.now(timezone.utc)
        order.status_reason = remote.get("reject_reason") or remote.get("status") or order.status_reason
        order.broker_status_raw = remote.get("status") or order.broker_status_raw

        status_map = {
            "new": OrderStatus.submitted,
            "accepted": OrderStatus.submitted,
            "accepted_for_bidding": OrderStatus.submitted,
            "pending_new": OrderStatus.submitted,
            "done_for_day": OrderStatus.submitted,
            "partially_filled": OrderStatus.partially_filled,
            "filled": OrderStatus.filled,
            "pending_cancel": OrderStatus.cancel_requested,
            "canceled": OrderStatus.canceled,
            "pending_replace": OrderStatus.replace_requested,
            "replaced": OrderStatus.replaced,
            "expired": OrderStatus.expired,
            "rejected": OrderStatus.failed,
        }
        order.status = status_map.get(remote_status, order.status)

        filled_avg = remote.get("filled_avg_price")
        if filled_avg not in (None, ""):
            order.filled_price = float(filled_avg)
            order.average_fill_price = float(filled_avg)
        filled_qty = remote.get("filled_qty")
        if filled_qty not in (None, ""):
            order.filled_quantity = int(float(filled_qty))
        elif order.status == OrderStatus.filled:
            order.filled_quantity = order.quantity
        order.remaining_quantity = max(order.quantity - order.filled_quantity, 0)

        submitted_at = remote.get("submitted_at")
        if submitted_at and order.submitted_at is None:
            order.submitted_at = self._parse_datetime(submitted_at)

        filled_at = remote.get("filled_at")
        if filled_at:
            order.filled_at = self._parse_datetime(filled_at)
        canceled_at = remote.get("canceled_at")
        if canceled_at:
            order.canceled_at = self._parse_datetime(canceled_at)
        updated_at = remote.get("updated_at") or filled_at or canceled_at or submitted_at
        if updated_at:
            order.broker_updated_at = self._parse_datetime(updated_at)

        if not order.broker_name:
            order.broker_name = BrokerName.alpaca
        if not order.broker_environment:
            order.broker_environment = BrokerEnvironment.paper
        return order

    def _parse_datetime(self, raw: str) -> datetime:
        normalized = raw.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized).astimezone(timezone.utc)

    def get_broker_name(self) -> str:
        return "alpaca"

    def cancel_order(self, order: OrderRecord) -> OrderRecord:
        if not order.broker_order_id:
            raise ValueError("Broker order id is required to cancel an Alpaca order.")
        response = self._request("DELETE", f"/orders/{order.broker_order_id}")
        remote = self._extract_json(response) or {
            "id": order.broker_order_id,
            "status": "canceled",
            "canceled_at": datetime.now(timezone.utc).isoformat(),
        }
        return self._merge_remote_order(order, remote)

    def replace_order(self, order: OrderRecord, *, quantity: int | None, limit_price: float | None) -> OrderRecord:
        if not order.broker_order_id:
            raise ValueError("Broker order id is required to replace an Alpaca order.")
        payload: dict[str, Any] = {}
        if quantity is not None:
            payload["qty"] = str(quantity)
        if limit_price is not None:
            payload["limit_price"] = str(limit_price)
        remote = self._extract_json(self._request("PATCH", f"/orders/{order.broker_order_id}", json=payload)) or {}
        return self._merge_remote_order(order, remote)

    def _extract_json(self, response) -> dict[str, Any] | None:
        try:
            payload = response.json()
        except ValueError:
            return None
        if isinstance(payload, dict):
            return payload
        return None

    def _build_default_session(self):
        try:
            import requests  # type: ignore
        except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError(
                "requests is required for Alpaca API mode. Install dependencies or inject a session."
            ) from exc

        return requests.Session()

    def _format_transport_error(self, path: str, exc: Exception) -> str:
        message = str(exc)
        lowered = message.lower()
        if "ssl" in lowered or "tls" in lowered:
            return (
                f"Alpaca API request to {path} failed during TLS/SSL setup. "
                "Check local certificate/network settings or switch back to simulator mode."
            )
        if "timed out" in lowered or "timeout" in lowered:
            return (
                f"Alpaca API request to {path} timed out. "
                "Check connectivity to the paper endpoint and retry."
            )
        return f"Alpaca API request to {path} failed before the broker responded: {message}"

    def _format_http_error(self, path: str, response, exc: Exception) -> str:
        status_code = getattr(response, "status_code", None)
        body = getattr(response, "text", "") or ""
        snippet = body.strip().replace("\n", " ")
        if len(snippet) > 200:
            snippet = snippet[:200] + "..."

        if status_code == 401:
            return (
                f"Alpaca API request to {path} was rejected with 401 Unauthorized. "
                "Verify the paper API key/secret and confirm the backend was restarted after editing .env."
            )
        if status_code:
            detail = f" Response: {snippet}" if snippet else ""
            return f"Alpaca API request to {path} failed with HTTP {status_code}.{detail}"
        return f"Alpaca API request to {path} failed: {exc}"
