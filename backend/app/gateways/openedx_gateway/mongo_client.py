"""Thin async wrapper around Motor for Open edX's MongoDB (RF-22).

Every failure mode (not configured, unreachable, bad collection) surfaces as
OpenEdxMongoUnavailableError so callers can degrade gracefully instead of
crashing the app — Open edX may simply not be reachable from dev.
"""
import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


class OpenEdxMongoUnavailableError(RuntimeError):
    """Open edX MongoDB is not configured or not reachable."""


class OpenEdxMongoClient:
    def __init__(
        self,
        url: str | None = None,
        db_name: str | None = None,
        timeout_ms: int = 5000,
    ):
        self.url = url if url is not None else settings.openedx_mongo_url
        self.db_name = db_name if db_name is not None else settings.openedx_mongo_db
        self.timeout_ms = timeout_ms
        self._client = None

    @property
    def is_configured(self) -> bool:
        return bool(self.url and self.db_name)

    def _database(self):
        if not self.is_configured:
            raise OpenEdxMongoUnavailableError(
                "Open edX MongoDB is not configured. Set OPENEDX_MONGO_URL and "
                "OPENEDX_MONGO_DB to enable the gateway."
            )
        if self._client is None:
            # Imported lazily so the app does not pay for (or fail on) the driver
            # when the gateway is disabled.
            from motor.motor_asyncio import AsyncIOMotorClient

            self._client = AsyncIOMotorClient(
                self.url, serverSelectionTimeoutMS=self.timeout_ms
            )
        return self._client[self.db_name]

    async def ping(self) -> bool:
        """Raise OpenEdxMongoUnavailableError unless the server answers."""
        database = self._database()
        try:
            await database.command("ping")
        except OpenEdxMongoUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001 — any driver error means unreachable
            raise OpenEdxMongoUnavailableError(
                f"Cannot reach Open edX MongoDB at {self.url}: {exc}"
            ) from exc
        return True

    async def fetch(
        self, collection: str, query: dict | None = None
    ) -> list[dict[str, Any]]:
        database = self._database()
        try:
            cursor = database[collection].find(query or {})
            return await cursor.to_list(length=None)
        except OpenEdxMongoUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise OpenEdxMongoUnavailableError(
                f"Failed reading '{collection}' from Open edX MongoDB: {exc}"
            ) from exc

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
