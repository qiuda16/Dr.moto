import xmlrpc.client
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

class OdooClient:
    def __init__(self):
        self.url = settings.ODOO_URL
        self.db = settings.ODOO_DB
        self.username = settings.ODOO_USER
        self.password = settings.ODOO_PASSWORD
        self.uid = None
        
    def authenticate(self):
        if self.uid:
            return self.uid
        
        try:
            common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
            self.uid = common.authenticate(self.db, self.username, self.password, {})
            if not self.uid:
                logger.error("Odoo authentication failed")
                return None
            logger.info(f"Authenticated with Odoo (UID: {self.uid})")
            return self.uid
        except Exception as e:
            logger.error(f"Failed to connect to Odoo: {e}")
            return None

    def execute_kw(self, model, method, args, kwargs=None):
        if not self.uid:
            if not self.authenticate():
                raise Exception("Not authenticated with Odoo")
        
        if kwargs is None:
            kwargs = {}
            
        models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
        return models.execute_kw(self.db, self.uid, self.password, model, method, args, kwargs)

odoo_client = OdooClient()
