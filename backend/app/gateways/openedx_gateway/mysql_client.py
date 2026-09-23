"""Thin async wrapper around aiomysql for Open edX's MySQL (RF-22).

Mirrors mongo_client.py: every failure mode (not configured, unreachable, bad
query) surfaces as OpenEdxMySQLUnavailableError so callers can degrade
gracefully instead of crashing the app. Open edX's enrollments live in MySQL
(student_courseenrollment), so the gateway reads them here rather than in Mongo.
"""
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class OpenEdxMySQLUnavailableError(RuntimeError):
    """Open edX MySQL is not configured or not reachable."""


class OpenEdxMySQLClient:
    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        user: str | None = None,
        password: str | None = None,
        db: str | None = None,
    ):
        self.host = host if host is not None else settings.openedx_mysql_host
        self.port = port if port is not None else settings.openedx_mysql_port
        self.user = user if user is not None else settings.openedx_mysql_user
        self.password = (
            password if password is not None else settings.openedx_mysql_password
        )
        self.db = db if db is not None else settings.openedx_mysql_db
        self._pool = None

    @property
    def is_configured(self) -> bool:
        return bool(self.host and self.user and self.db)

    async def _get_pool(self):
        if not self.is_configured:
            raise OpenEdxMySQLUnavailableError(
                "Open edX MySQL is not configured. Set OPENEDX_MYSQL_HOST, "
                "OPENEDX_MYSQL_USER and OPENEDX_MYSQL_DB to enable enrollment sync."
            )
        if self._pool is None:
            # Imported lazily so the app does not pay for (or fail on) the driver
            # when the gateway is disabled.
            import aiomysql

            try:
                self._pool = await aiomysql.create_pool(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password or "",
                    db=self.db,
                    minsize=1,
                    maxsize=3,
                    autocommit=True,
                )
            except Exception as exc:  # noqa: BLE001 — any driver error means unreachable
                raise OpenEdxMySQLUnavailableError(
                    f"Cannot connect to Open edX MySQL at {self.host}:{self.port}: {exc}"
                ) from exc
        return self._pool

    async def ping(self) -> bool:
        """Raise OpenEdxMySQLUnavailableError unless the server answers."""
        pool = await self._get_pool()
        try:
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1")
                    await cur.fetchone()
        except OpenEdxMySQLUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise OpenEdxMySQLUnavailableError(
                f"Cannot reach Open edX MySQL at {self.host}:{self.port}: {exc}"
            ) from exc
        return True

    async def fetch_all(self, sql: str, params: tuple | None = None) -> list[dict]:
        # aiomysql imported lazily (same reason as _get_pool): keeps importing
        # this module cheap and driver-free when the gateway is disabled.
        import aiomysql

        pool = await self._get_pool()
        try:
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(sql, params or ())
                    rows = await cur.fetchall()
                    return list(rows)
        except OpenEdxMySQLUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise OpenEdxMySQLUnavailableError(
                f"Failed running query on Open edX MySQL: {exc}"
            ) from exc

    def close(self) -> None:
        if self._pool is not None:
            self._pool.close()
            self._pool = None
