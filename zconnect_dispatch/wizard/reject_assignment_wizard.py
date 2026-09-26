from odoo import models, fields, api, _

class RejectAssignmentWizard(models.TransientModel):
    _name = 'zconnect.dispatch.reject.wizard'
    _description = 'Reject Assignment Wizard'

    assignment_id = fields.Many2one('zconnect.dispatch.assignment', string='Assignment', required=True, readonly=True)
    rejection_reason = fields.Text(string='Rejection Reason', required=True)

    def action_reject(self):
        self.ensure_one()
        self.assignment_id.action_reject(self.rejection_reason)
        return {'type': 'ir.actions.act_window_close'}
