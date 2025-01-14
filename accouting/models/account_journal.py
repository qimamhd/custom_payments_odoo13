# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, date
import datetime


class xx_account_journal(models.Model):
    _inherit = 'account.journal'
    
    
    multi_payment_journal_id = fields.Boolean(string="دفتر سندات القبض والصرف",copy=False,)
