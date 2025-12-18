import xmlrpc.client
import requests
import random
import time

# Configuration
ODOO_URL = "http://localhost:8069"
ODOO_DB = "odoo"
ODOO_USER = "admin"
ODOO_PASSWORD = "admin"
BFF_URL = "http://localhost:8080"

def connect_odoo():
    print("Connecting to Odoo...")
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
    if not uid:
        raise Exception("Authentication failed")
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
    return uid, models

def seed_customers(uid, models):
    print("\n--- Seeding Customer Library (20+ records) ---")
    
    # Base names for generating random customers
    first_names = ["James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles", "Zhang", "Li", "Wang", "Liu", "Chen"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "San", "Si", "Wu", "Wei", "Dong"]
    cities = ["Beijing", "Shanghai", "Guangzhou", "Shenzhen", "New York", "London", "Tokyo", "Berlin", "Paris", "Chengdu"]
    
    customers = []
    
    # 1. Edge/Specific Cases
    customers.append({"name": "VVIP Client", "email": "vvip@drmoto.com", "phone": "10000000000", "city": "Beijing", "comment": "High value customer"})
    customers.append({"name": "Bad Payer", "email": "debt@unknown.com", "phone": "00000000000", "city": "Nowhere", "comment": "Always late"})
    customers.append({"name": "Motorcycle Club South", "email": "club_south@moto.com", "is_company": True, "city": "Guangzhou"})
    
    # 2. Random Generation
    for i in range(25):
        fname = random.choice(first_names)
        lname = random.choice(last_names)
        name = f"{fname} {lname}"
        email = f"{fname.lower()}.{lname.lower()}{i}@example.com"
        phone = f"13{random.randint(0,9)}{random.randint(10000000, 99999999)}"
        city = random.choice(cities)
        
        customers.append({
            "name": name,
            "email": email,
            "phone": phone,
            "city": city,
            "street": f"{random.randint(1,999)} {random.choice(['Main St', 'Second Ave', 'Park Rd'])}"
        })

    count = 0
    for c in customers:
        existing = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'res.partner', 'search_count', [[['name', '=', c['name']]]])
        if existing == 0:
            models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'res.partner', 'create', [c])
            count += 1
    
    print(f"Seeded {count} new customers.")

def seed_products_and_prices(uid, models):
    print("\n--- Seeding Pricing Library (Products & Strategies) ---")
    
    # 1. Products (20+ items)
    product_templates = [
        # Oil
        {"name": "Motul 7100 10W-40 1L", "list_price": 120.0, "standard_price": 80.0, "categ": "Oil"},
        {"name": "Motul 300V 10W-40 1L", "list_price": 180.0, "standard_price": 130.0, "categ": "Oil"},
        {"name": "Shell Advance Ultra 10W-40", "list_price": 90.0, "standard_price": 60.0, "categ": "Oil"},
        {"name": "Castrol Power1 10W-40", "list_price": 85.0, "standard_price": 55.0, "categ": "Oil"},
        # Filters
        {"name": "Oil Filter KN-303", "list_price": 85.0, "standard_price": 40.0, "categ": "Parts"},
        {"name": "Oil Filter KN-204", "list_price": 85.0, "standard_price": 40.0, "categ": "Parts"},
        {"name": "Oil Filter HF-204", "list_price": 45.0, "standard_price": 20.0, "categ": "Parts"},
        # Tires
        {"name": "Pirelli Diablo Rosso IV (Front 120/70)", "list_price": 1200.0, "standard_price": 800.0, "categ": "Tires"},
        {"name": "Pirelli Diablo Rosso IV (Rear 180/55)", "list_price": 1800.0, "standard_price": 1200.0, "categ": "Tires"},
        {"name": "Michelin Road 6 (Front)", "list_price": 1250.0, "standard_price": 850.0, "categ": "Tires"},
        {"name": "Michelin Road 6 (Rear)", "list_price": 1850.0, "standard_price": 1250.0, "categ": "Tires"},
        # Brakes
        {"name": "Brembo SC Brake Pads (Front)", "list_price": 450.0, "standard_price": 300.0, "categ": "Brakes"},
        {"name": "EBC Double-H Brake Pads", "list_price": 380.0, "standard_price": 250.0, "categ": "Brakes"},
        {"name": "Brembo RCS19 Master Cylinder", "list_price": 2500.0, "standard_price": 1800.0, "categ": "Brakes"},
        # Care
        {"name": "Chain Cleaner (500ml)", "list_price": 50.0, "standard_price": 25.0, "categ": "Care"},
        {"name": "Chain Lube (500ml)", "list_price": 60.0, "standard_price": 30.0, "categ": "Care"},
        {"name": "Bike Wash Shampoo", "list_price": 40.0, "standard_price": 15.0, "categ": "Care"},
        # Gear
        {"name": "DrMoto T-Shirt", "list_price": 99.0, "standard_price": 30.0, "categ": "Gear"},
        {"name": "Riding Gloves (Leather)", "list_price": 399.0, "standard_price": 200.0, "categ": "Gear"},
        {"name": "Phone Mount", "list_price": 150.0, "standard_price": 80.0, "categ": "Accessories"},
        {"name": "USB Charger", "list_price": 80.0, "standard_price": 30.0, "categ": "Accessories"},
    ]

    prod_count = 0
    for p in product_templates:
        existing = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'product.product', 'search_count', [[['name', '=', p['name']]]])
        if existing == 0:
            models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'product.product', 'create', [{
                'name': p['name'],
                'list_price': p['list_price'],
                'standard_price': p['standard_price'],
                'type': 'consu', # Fallback to consumable if stock module is missing
            }])
            prod_count += 1
    print(f"Seeded {prod_count} new products.")

    # 2. Pricelists (Strategies)
    # Check if 'product.pricelist' exists (it should)
    try:
        strategies = [
            {"name": "VIP Member (15% Off)", "discount": 15.0},
            {"name": "Club Discount (10% Off)", "discount": 10.0},
            {"name": "Summer Sale (5% Off)", "discount": 5.0},
            {"name": "Staff Price (Cost + 10%)", "discount": 0.0, "formula": True} # Simplified for now
        ]
        
        for s in strategies:
            existing = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'product.pricelist', 'search', [[['name', '=', s['name']]]])
            if not existing:
                # Create Pricelist
                pl_id = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'product.pricelist', 'create', [{
                    'name': s['name'],
                }])
                
                # Create Item (Rule)
                # Apply to all products (applied_on='3_global')
                # Compute price: formula = list_price * (1 - discount/100)
                # In Odoo: compute_price='formula', base='list_price', price_discount=discount
                
                models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'product.pricelist.item', 'create', [{
                    'pricelist_id': pl_id,
                    'applied_on': '3_global',
                    'compute_price': 'formula',
                    'base': 'list_price', # Public Price
                    'price_discount': s.get('discount', 0.0)
                }])
                print(f"Created Pricelist Strategy: {s['name']}")
            else:
                print(f"Pricelist {s['name']} exists.")
                
    except Exception as e:
        print(f"Warning: Could not seed pricelists (Module might be missing or access denied): {e}")

def main():
    try:
        uid, models = connect_odoo()
        seed_customers(uid, models)
        seed_products_and_prices(uid, models)
        print("\n=== Library Data Seed Complete ===")
    except Exception as e:
        print(f"FATAL ERROR: {e}")

if __name__ == "__main__":
    main()
