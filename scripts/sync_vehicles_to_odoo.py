import requests
import xmlrpc.client
import time

BFF_URL = "http://localhost:8080"
ODOO_URL = "http://localhost:8069"
ODOO_DB = "odoo"
ODOO_USER = "admin"
ODOO_PASSWORD = "admin"

def get_bff_vehicles():
    print("Fetching vehicles from BFF...")
    try:
        res = requests.get(f"{BFF_URL}/mp/knowledge/vehicles")
        if res.status_code == 200:
            return res.json()
        else:
            print(f"Failed to fetch vehicles: {res.status_code}")
            return []
    except Exception as e:
        print(f"Error connecting to BFF: {e}")
        return []

def sync_to_odoo(vehicles):
    print("Connecting to Odoo...")
    try:
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
        
        if not uid:
            print("Authentication failed")
            return

        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
        
        # Check if model exists
        try:
            models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'drmoto.vehicle', 'check_access_rights', ['read'], {'raise_exception': False})
        except Exception as e:
            print(f"Model drmoto.vehicle not found or access denied. Please upgrade the Odoo module. Error: {e}")
            return

        print(f"Syncing {len(vehicles)} vehicles...")
        count = 0
        for v in vehicles:
            # Check if exists
            existing = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'drmoto.vehicle', 'search_read', [[['key', '=', v['key']]]], {'fields': ['id'], 'limit': 1})
            
            vals = {
                'key': v['key'],
                'make': v['make'],
                'model': v['model'],
                'year_from': v['year_from'],
                'year_to': v.get('year_to') or 0,
                'engine_code': v.get('engine_code') or '',
            }
            
            if existing:
                # Update
                models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'drmoto.vehicle', 'write', [[existing[0]['id']], vals])
            else:
                # Create
                models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'drmoto.vehicle', 'create', [vals])
            count += 1
            if count % 10 == 0:
                print(f"Synced {count}...")
                
        print("Sync complete!")
        
    except Exception as e:
        print(f"Odoo Sync Error: {e}")

if __name__ == "__main__":
    vehicles = get_bff_vehicles()
    if vehicles:
        sync_to_odoo(vehicles)
