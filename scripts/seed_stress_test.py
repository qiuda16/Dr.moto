import xmlrpc.client
import random
import time

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

def seed_stress_data():
    uid, models = connect_odoo()
    
    # 1. Find James
    partners = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'res.partner', 'search_read', [[['phone', '=', '13800000000']]], {'limit': 1})
    if not partners:
        print("Demo user James not found! Please run basic seed first.")
        return
    
    james_id = partners[0]['id']
    print(f"Seeding data for Customer: {partners[0]['name']} (ID: {james_id})")

    # 2. Add More Vehicles (Test Horizontal Scroll)
    extra_bikes = [
        {'vin': 'BMWS1000RR2024', 'plate': '京B-BMW01', 'model': 'BMW S1000RR'},
        {'vin': 'DUCATIV4S2024', 'plate': '京A-DUC01', 'model': 'Ducati Panigale V4'},
        {'vin': 'HD883IRON2023', 'plate': '京A-HD883', 'model': 'Harley-Davidson Iron 883'},
    ]
    
    # Get or Create Model IDs (Simplification: Just assume a generic model or create if possible, 
    # but to be safe we will look for existing fleet.vehicle.model or just reuse the one we have if search fails)
    # Actually, let's just create generic partner vehicles.
    
    # Find a vehicle model to reuse
    v_models = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'fleet.vehicle.model', 'search', [[]], {'limit': 1})
    model_id = v_models[0] if v_models else False
    
    for bike in extra_bikes:
        # Check if exists
        exists = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'drmoto.partner.vehicle', 'search', [[['license_plate', '=', bike['plate']]]])
        if not exists:
            models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'drmoto.partner.vehicle', 'create', [{
                'partner_id': james_id,
                'vehicle_id': model_id, # Reuse generic model for now
                'license_plate': bike['plate'],
                'vin': bike['vin'],
                'color': 'black'
            }])
            print(f"Added Vehicle: {bike['plate']}")

    # 3. Create History Orders (Test List Performance & Scroll)
    history_tasks = [
        ('Oil Change', 150), ('Tire Swap', 300), ('Chain Lube', 50), 
        ('Brake Check', 80), ('Winter Storage', 200), ('Spring Prep', 180),
        ('Battery Replace', 120), ('Coolant Flush', 90), ('Mirror Fix', 40),
        ('Detailing', 100)
    ]
    
    for task, price in history_tasks:
        order_id = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'drmoto.work.order', 'create', [{
            'customer_id': james_id,
            'vehicle_plate': '京A-98720',
            'description': f"Historic: {task}",
            'state': 'done',
            'date_planned': '2024-01-01' # Odoo will handle date format
        }])
        # Note: 'amount_total' is computed, so we might need to add lines to make it non-zero.
        # Let's add a dummy line
        prod_ids = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'product.product', 'search', [[]], {'limit': 1})
        if prod_ids:
             models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'drmoto.work.order.line', 'create', [{
                'work_order_id': order_id,
                'product_id': prod_ids[0],
                'name': task,
                'quantity': 1,
                'price_unit': price
             }])
    print(f"Created {len(history_tasks)} history orders.")

    # 4. Create a Complex Quoted Order (Test Detail View & Line Items)
    complex_order_id = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'drmoto.work.order', 'create', [{
        'customer_id': james_id,
        'vehicle_plate': '京B-BMW01',
        'description': 'Major Accident Repair - Front End Rebuild',
        'state': 'quoted'
    }])
    
    parts = [
        ('Front Fork Left', 800), ('Front Fork Right', 800), ('Wheel Rim', 500),
        ('Tire Front', 200), ('Brake Disc L', 150), ('Brake Disc R', 150),
        ('Fender', 100), ('Headlight Assembly', 600), ('Handlebar', 120),
        ('Labor: Disassembly', 300), ('Labor: Assembly', 400), ('Labor: Testing', 100)
    ]
    
    if prod_ids:
        for part_name, price in parts:
            models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'drmoto.work.order.line', 'create', [{
                'work_order_id': complex_order_id,
                'product_id': prod_ids[0], # Reuse generic product
                'name': part_name,
                'quantity': 1,
                'price_unit': price
            }])
    
    print("Created complex 'Quoted' order with 12 line items.")

    # 5. Create an In-Progress Order (Test Home Active Card)
    models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'drmoto.work.order', 'create', [{
        'customer_id': james_id,
        'vehicle_plate': '京A-DUC01',
        'description': 'Track Day Prep - In Progress',
        'state': 'in_progress'
    }])
    print("Created 'In Progress' order.")

    print("\n=== DATA SEEDING COMPLETE ===")
    print("Please refresh the Mini Program.")

if __name__ == "__main__":
    seed_stress_data()
