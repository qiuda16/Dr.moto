import xmlrpc.client
import requests
import random

# Configuration
ODOO_URL = "http://localhost:8069"
ODOO_DB = "odoo"
ODOO_USER = "admin"
ODOO_PASSWORD = "admin"

def connect_odoo():
    print("Connecting to Odoo...")
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
    if not uid:
        raise Exception("Authentication failed")
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
    return uid, models

def seed_links(uid, models):
    print("\n--- Linking Customer -> Vehicle -> Procedure -> Price ---")

    # 1. Link Customer -> Vehicle (Create "My Garage")
    # Find some customers
    customers = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'res.partner', 'search_read', [[['is_company', '=', False]]], {'fields': ['id', 'name'], 'limit': 10})
    
    # Find some vehicle models
    ninja400 = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'drmoto.vehicle', 'search_read', [[['model', 'ilike', 'Ninja 400']]], {'limit': 1})
    cbr650 = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'drmoto.vehicle', 'search_read', [[['model', 'ilike', 'CBR650']]], {'limit': 1})
    
    vehicles_pool = []
    if ninja400: vehicles_pool.append(ninja400[0])
    if cbr650: vehicles_pool.append(cbr650[0])
    
    if not vehicles_pool:
        print("No vehicle models found. Run vehicle sync first.")
        return

    # Assign bikes to customers
    for cust in customers:
        # Check if already has vehicle
        existing = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'drmoto.partner.vehicle', 'search_count', [[['partner_id', '=', cust['id']]]])
        if existing == 0:
            v_model = random.choice(vehicles_pool)
            plate = f"京A{random.randint(10000, 99999)}"
            
            models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'drmoto.partner.vehicle', 'create', [{
                'partner_id': cust['id'],
                'vehicle_id': v_model['id'],
                'license_plate': plate,
                'color': random.choice(['Green', 'Black', 'Red', 'White']),
                'vin': f"L{random.randint(1000000000000000, 9999999999999999)}"
            }])
            print(f"Assigned {v_model['model']} ({plate}) to {cust['name']}")

    # 2. Link Procedure -> Parts (Cost Calculation)
    # Find "Oil Change (Ninja 400)" procedure
    procs = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'drmoto.procedure', 'search_read', [[['name', 'ilike', 'Oil Change']]], {'fields': ['id', 'name']})
    
    if not procs:
        print("No procedures found. Run full seed first.")
        return

    # Find Parts (Oil, Filter)
    oil = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'product.product', 'search_read', [[['name', 'ilike', 'Motul 7100']]], {'limit': 1})
    filter_kn = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'product.product', 'search_read', [[['name', 'ilike', 'KN-303']]], {'limit': 1})
    
    if oil and filter_kn:
        oil_id = oil[0]['id']
        filter_id = filter_kn[0]['id']
        
        for p in procs:
            # Check if parts already linked
            parts_count = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'drmoto.procedure.part', 'search_count', [[['procedure_id', '=', p['id']]]])
            
            if parts_count == 0:
                # Add Oil (2.0L)
                models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'drmoto.procedure.part', 'create', [{
                    'procedure_id': p['id'],
                    'product_id': oil_id,
                    'quantity': 2.0
                }])
                # Add Filter (1 Unit)
                models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'drmoto.procedure.part', 'create', [{
                    'procedure_id': p['id'],
                    'product_id': filter_id,
                    'quantity': 1.0
                }])
                print(f"Linked Parts to {p['name']}: 2L Oil + 1 Filter")
            else:
                print(f"Procedure {p['name']} already has parts linked.")

def main():
    try:
        uid, models = connect_odoo()
        seed_links(uid, models)
        print("\n=== Data Linking Complete ===")
    except Exception as e:
        print(f"FATAL ERROR: {e}")

if __name__ == "__main__":
    main()
