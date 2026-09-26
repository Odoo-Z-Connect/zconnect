from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError

class TestDashboard(TransactionCase):
    def setUp(self):
        super(TestDashboard, self).setUp()
        self.Dashboard = self.env['zconnect.dashboard']
        self.user_admin = self.env.ref('base.user_admin')
        
        # Create dispatcher user
        self.user_dispatcher = self.env['res.users'].create({
            'name': 'Test Dispatcher',
            'login': 'dispatcher_test',
            'group_ids': [(6, 0, [self.env.ref('zconnect_base.group_zconnect_dispatcher').id, self.env.ref('base.group_user').id])]
        })
        
        # Create manager user
        self.user_manager = self.env['res.users'].create({
            'name': 'Test Manager',
            'login': 'manager_test',
            'group_ids': [(6, 0, [self.env.ref('zconnect_base.group_zconnect_manager').id, self.env.ref('base.group_user').id])]
        })

    def test_dashboard_access(self):
        # Admin
        data = self.Dashboard.with_user(self.user_admin).get_dashboard_data()
        self.assertTrue(data['has_finance_access'])
        
        # Manager
        data = self.Dashboard.with_user(self.user_manager).get_dashboard_data()
        self.assertTrue(data['has_finance_access'])
        
        # Dispatcher
        data = self.Dashboard.with_user(self.user_dispatcher).get_dashboard_data()
        self.assertFalse(data['has_finance_access'])
        
        # Internal User (no ZConnect roles)
        user_basic = self.env['res.users'].create({
            'name': 'Basic User',
            'login': 'basic_test',
            'group_ids': [(6, 0, [self.env.ref('base.group_user').id])]
        })
        with self.assertRaises(AccessError):
            self.Dashboard.with_user(user_basic).get_dashboard_data()
