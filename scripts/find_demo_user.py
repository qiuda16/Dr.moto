import xmlrpc.client

# Configuration
ODOO_URL = "http://localhost:8069"
ODOO_DB = "odoo"
ODOO_USER = "admin"
ODOO_PASSWORD = "admin"

def connect_odoo():
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
    return uid, models

def find_demo_user():
    uid, models = connect_odoo()
    
    # Find a vehicle first, to ensure the user has data
    vehicles = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'drmoto.partner.vehicle', 'search_read', [[]], {'limit': 1, 'fields': ['partner_id', 'license_plate']})
    
    if not vehicles:
        print("No vehicles found in DB. Please run seed script first.")
        return

    partner_data = vehicles[0]['partner_id'] # [id, name]
    partner_id = partner_data[0]
    partner_name = partner_data[1]
    
    # Get full partner details
    partner = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'res.partner', 'read', [[partner_id], ['name', 'phone', 'email']])[0]
    
    print("\n=== DEMO USER CREDENTIALS ===")
    print(f"Name: {partner['name']}")
    print(f"Phone: {partner['phone'] or 'N/A'}")
    print(f"Vehicle: {vehicles[0]['license_plate']}")
    print("===========================\n")
    print(f"Use '{partner['name']}' to login in the App.")

if __name__ == "__main__":
    find_demo_user()
