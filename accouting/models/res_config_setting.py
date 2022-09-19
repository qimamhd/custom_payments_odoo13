
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    auto_payment_posted = fields.Boolean(string="ترحيل السندات القبض والصرف اليا للحسابات بعد اعتمادها ", default=False)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        l_auto_payment_posted = params.get_param('auto_payment_posted',
                                                 default=False)
        res.update(auto_payment_posted=l_auto_payment_posted)
        return res

    def set_values(self):
        if self.auto_payment_posted:
            # check_exit_payments = self.env['account.move'].search([('custom_payment_id', '>', 0), ('state', '!=', 'posted')])
            # if check_exit_payments:
            #     super(ResConfigSettings, self).set_values()
            #     self.env['ir.config_parameter'].sudo().set_param(
            #         "auto_payment_posted",
            #         False)
            #     raise ValidationError("يجب ترحيل كل السندات الغير مرحلة اولا قبل تفعيل الخيار")
            # else:
            super(ResConfigSettings, self).set_values()
            self.env['ir.config_parameter'].sudo().set_param(
                "auto_payment_posted",
                self.auto_payment_posted)

        else:
            super(ResConfigSettings, self).set_values()
            self.env['ir.config_parameter'].sudo().set_param(
                "auto_payment_posted",
                self.auto_payment_posted)
