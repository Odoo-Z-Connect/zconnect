# -*- coding: utf-8 -*-
"""
Automated Test & Verification Script for Zimbabwe Connect - Step 1 Foundation
"""
import sys
sys.path.insert(0, r'C:\Program Files\OdooDeploymentEngine\odoo-source')

import odoo
from odoo import api, fields
from odoo.modules.registry import Registry

config_path = r'C:\Program Files\OdooDeploymentEngine\enterprise\instances\odoo_enterprise_8070\odoo-enterprise.conf'
odoo.tools.config.parse_config(['-c', config_path])

db_name = 'odoo_enterprise'
reg = Registry(db_name)

print("=" * 70)
print("RUNNING STEP 1 AUTOMATED VERIFICATION TEST SUITE")
print("=" * 70)

with reg.cursor() as cr:
    env = api.Environment(cr, odoo.SUPERUSER_ID, {})
    
    # 1. Verify Module Installation Status
    module = env['ir.module.module'].search([('name', '=', 'zconnect_base')])
    assert module.exists(), "zconnect_base module record not found in ir_module_module!"
    assert module.state == 'installed', f"Expected installed state, got {module.state}"
    print(f"[PASS] 1. Module 'zconnect_base' is installed (Version: {module.latest_version})")

    # 2. Verify Security Groups
    expected_groups = [
        'group_zconnect_customer',
        'group_zconnect_driver',
        'group_zconnect_dispatcher',
        'group_zconnect_finance',
        'group_zconnect_manager',
        'group_zconnect_admin'
    ]
    for xml_id in expected_groups:
        grp = env.ref(f'zconnect_base.{xml_id}', raise_if_not_found=False)
        assert grp, f"Security group {xml_id} missing!"
        print(f"[PASS] 2. Security group '{grp.name}' (XML ID: {xml_id}) verified.")

    # 3. Test Partner Creation: Standard Normal Contact
    partner_normal = env['res.partner'].create({
        'name': 'Test Regular Supplier Ltd',
        'email': 'supplier@test.co.zw',
        'phone': '+263 242 111111',
        'zconnect_is_customer': False,
    })
    assert not partner_normal.zconnect_customer_code, f"Regular contact should NOT have customer code, found: {partner_normal.zconnect_customer_code}"
    print(f"[PASS] 3. Standard contact '{partner_normal.name}' created without customer code.")

    # 4. Test Partner Creation: ZConnect Customer
    partner_cus1 = env['res.partner'].create({
        'name': 'Test ZConnect Customer Alpha',
        'email': 'alpha@customer.co.zw',
        'phone': '+263 77 999 0001',
        'zconnect_is_customer': True,
    })
    code1 = partner_cus1.zconnect_customer_code
    assert code1 and code1.startswith('CUS-'), f"Customer code should start with CUS-, got: {code1}"
    print(f"[PASS] 4. ZConnect customer '{partner_cus1.name}' created with sequence code: {code1}")

    # 5. Test Partner Write: Convert Standard Contact to ZConnect Customer
    partner_normal.write({'zconnect_is_customer': True})
    code2 = partner_normal.zconnect_customer_code
    assert code2 and code2.startswith('CUS-'), f"Converted partner should receive customer code, got: {code2}"
    assert code1 != code2, f"Consecutive customer codes must be unique! ({code1} vs {code2})"
    print(f"[PASS] 5. Converted standard contact to ZConnect customer; generated new unique code: {code2}")

    # 6. Test Immutability: Subsequent Updates Do NOT Change Customer Code
    partner_normal.write({'phone': '+263 77 888 8888', 'name': 'Updated Regular Supplier Name'})
    assert partner_normal.zconnect_customer_code == code2, "Customer code unexpectedly changed during write!"
    print(f"[PASS] 6. Customer code '{code2}' preserved during subsequent partner updates.")

    # 7. Test Partner Search Filter Domains
    customers = env['res.partner'].search([('zconnect_is_customer', '=', True)])
    assert partner_cus1 in customers and partner_normal in customers, "ZConnect customer search domain failed!"
    print(f"[PASS] 7. Search filter for 'zconnect_is_customer' successfully retrieved {len(customers)} customers.")

    # Rollback test transactions to keep clean DB state
    cr.rollback()

print("=" * 70)
print("ALL STEP 1 VERIFICATION TESTS PASSED SUCCESSFULLY!")
print("=" * 70)
