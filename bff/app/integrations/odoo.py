import xmlrpc.client
import time
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)


class TimeoutTransport(xmlrpc.client.Transport):
    def __init__(self, timeout: int):
        super().__init__()
        self.timeout = timeout

    def make_connection(self, host):
        connection = super().make_connection(host)
        connection.timeout = self.timeout
        return connection


class OdooClient:
    def __init__(self):
        self.url = settings.ODOO_URL
        self.db = settings.ODOO_DB
        self.username = settings.ODOO_USER
        self.password = settings.ODOO_PASSWORD
        self.timeout_seconds = settings.ODOO_TIMEOUT_SECONDS
        self.max_attempts = max(1, settings.ODOO_RETRY_MAX_ATTEMPTS)
        self.backoff_seconds = max(0.0, settings.ODOO_RETRY_BACKOFF_SECONDS)
        self.uid = None
        self._transport = TimeoutTransport(timeout=self.timeout_seconds)
        self._common = xmlrpc.client.ServerProxy(
            f"{self.url}/xmlrpc/2/common", transport=self._transport, allow_none=True
        )
        self._models = xmlrpc.client.ServerProxy(
            f"{self.url}/xmlrpc/2/object", transport=self._transport, allow_none=True
        )

    def _sleep_before_retry(self, attempt: int):
        delay = self.backoff_seconds * (2 ** (attempt - 1))
        if delay > 0:
            time.sleep(delay)

    def _call_with_retry(self, operation_name: str, fn):
        last_error = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                return fn()
            except Exception as exc:
                last_error = exc
                if attempt < self.max_attempts:
                    logger.warning(
                        "odoo %s failed on attempt %s/%s: %s",
                        operation_name,
                        attempt,
                        self.max_attempts,
                        exc,
                    )
                    self._sleep_before_retry(attempt)
                    continue
                logger.error(
                    "odoo %s failed after %s attempts: %s",
                    operation_name,
                    self.max_attempts,
                    exc,
                )
        if last_error:
            raise last_error
        raise RuntimeError(f"Odoo {operation_name} failed unexpectedly")
        
    def ping(self):
        try:
            return bool(self._call_with_retry("ping", lambda: self._common.version()))
        except Exception:
            return False

    def authenticate(self, force: bool = False):
        if self.uid and not force:
            return self.uid
        
        try:
            self.uid = self._call_with_retry(
                "authenticate",
                lambda: self._common.authenticate(self.db, self.username, self.password, {}),
            )
            if not self.uid:
                logger.error("Odoo authentication failed")
                return None
            logger.info("Authenticated with Odoo (UID: %s)", self.uid)
            return self.uid
        except Exception as e:
            logger.error("Failed to connect to Odoo: %s", e)
            return None

    def execute_kw(self, model, method, args, kwargs=None):
        if not self.uid:
            if not self.authenticate():
                raise Exception("Not authenticated with Odoo")
        
        if kwargs is None:
            kwargs = {}

        def _execute():
            return self._models.execute_kw(
                self.db, self.uid, self.password, model, method, args, kwargs
            )

        try:
            return self._call_with_retry("execute_kw", _execute)
        except xmlrpc.client.Fault as exc:
            # Session or permission-related issues can be resolved by re-auth once.
            logger.warning("execute_kw fault on %s.%s: %s", model, method, exc)
            self.uid = None
            if not self.authenticate():
                raise
            return self._call_with_retry("execute_kw_reauth", _execute)

odoo_client = OdooClient()
