# -*- coding: utf-8 -*-

{
    'name': 'DrMoto MRO',
    'version': '1.0',
    'category': 'Services/Repair',
    'summary': 'Core MRO logic for DrMoto (Repair, Inventory, Work Orders)',
    'description': """
DrMoto MRO Module
=================
Handles:
- Work Order extensions
- Inventory moves logic
- Integration hooks for BFF
    """,
    'depends': ['base', 'mail', 'product', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/work_order_views.xml',
        'views/vehicle_views.xml',
        'views/procedure_views.xml',
        'views/library_views.xml',
        'views/partner_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
