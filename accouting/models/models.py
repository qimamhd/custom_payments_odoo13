# -*- coding: utf-8 -*-

from datetime import date
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT


class inheritaccount_move(models.Model):
    _inherit = 'account.move'

    custom_payment_id = fields.Integer()


class inheritaccount_move_line(models.Model):
    _inherit = 'account.move.line'

    custom_payment_line_id = fields.Integer()


class custom_payment(models.Model):
    _name = 'custom.account.payment'
    _inherit = ['mail.thread']

    _description = 'Accounting Payment'
    _rec_name = "payment_seq"

    payment_type = fields.Selection([
        ('receipt', 'Payment Receipt'),
        ('issue', 'Payment Issue')], required=True)

    payment_seq = fields.Integer(
        string='Payment sequence',
        invisible=True,
        copy=False,
        # # compute='_get_default_name'
        # default=lambda self: self._get_default_name(),
    )
    # company_branch_id = fields.Many2one(
    #     'res.company.branch',
    #     string="Branch",
    #     copy=False,
    #     readonly = True,
    #     required=True,
    #     # default=lambda self: self.env.user.company_branch_id.id,
    # )

    type_id = fields.Char()
    journal_id = fields.Many2one('account.journal', string='Journal', required=True,
                                 domain=[('multi_payment_journal_id','=',True),('type', '=', ['cash', 'bank'])])
    payment_date = fields.Date(default=date.today(), required=True)
    payment_state = fields.Selection([
        ('draft', 'Un Posted'),
        ('posted', 'Posted')], string='Payment State', required=True)
    local_amount = fields.Float(string='local_amount', readonly=True, required=True, compute='_calc_local_amount')
    payment_amt_char = fields.Char(readonly=True)
    owner_name = fields.Char()
    applied_by = fields.Char()
    pay_type = fields.Char()
    cost_cnr_id = fields.Many2one('account.analytic.account', string='Cost Center')
    owner_info_bank = fields.Char()
    desc = fields.Char(string='Description',)
    cheq_no = fields.Char()
    currency_id = fields.Many2one('res.currency', domain=[('active', '=', True)],
                                  default=lambda self: self.env.company.currency_id, required=True)
    curr_rate = fields.Float(string='Currency rate', required=True, default=1, compute='_get_rate')
    payment_amount = fields.Float(string='Payment amount', required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    paymt_lines = fields.One2many('custom.account.payment.line', 'pymt_id', required=True)
    user_id = fields.Many2one('res.users', string='User name', readonly=True, copy=False, tracking=True,
                              default=lambda self: self.env.uid)
    check_multi_currency = fields.Boolean(default=lambda self: self._default_multi_currency_policy())
    total_dr = fields.Float(string="Total Debit", readonly=True, compute='_calc_local_amount')
    total_cr = fields.Float(string="Total Credit", readonly=True, compute='_calc_local_amount')
    account_move_seq = fields.Char()
    check_auto_posted = fields.Boolean(compute="_default_auto_posted_policy")
    sales_man_id = fields.Many2one('custom.sales.mans', string='مندوب المبيعات')
    branch_id = fields.Many2one('custom.branches', string='الفرع', copy=False, readonly="True", required=True,
                                default=lambda self: self.env.user.branch_id.id)
    
    # _sql_constraints = [
    #     ('payment_seq_uniq', 'unique(payment_seq,payment_type)',
    #      'تنبيه.. رقم السند مكرر لنفس النوع'),
    # ]

    def _default_auto_posted_policy(self):
        """ Check custom sequence """
        params = self.env['ir.config_parameter'].sudo()
        l_auto_payment_posted = params.get_param('auto_payment_posted')
        print(l_auto_payment_posted)
        for rec in self:
            rec.check_auto_posted = True if l_auto_payment_posted else False

    # ===========================================================================================
    # @api.model
    # def _get_default_report_id(self):
    #     if self.env.context.get('report_name', False):
    #         return self.env.context.get('report_name', False)
    #     return self.env.ref('account_dynamic_reports.ins_account_financial_report_profitandloss0').id

    @api.depends('currency_id', 'payment_date', 'check_multi_currency')
    def _get_rate(self):
        if self.check_multi_currency and (self.currency_id != self.env.company.currency_id):
            l_rate = self.env['res.currency.rate'].search(
                [('company_id', '=', self.company_id.id), ('currency_id', '=', self.currency_id.id),
                 ('name', '=', self.payment_date)])
            if l_rate:
                self.curr_rate = l_rate.rate
                self.paymt_lines.curr_rate = l_rate.rate
                self.paymt_lines.currency_id = self.currency_id
            else:
                raise ValidationError('لا توجد سعر صرف للعملة المحدد يجب ادخال اسعار الصرف من شاشة العملات')
        else:
            self.curr_rate = 1
            self.paymt_lines.curr_rate = self.curr_rate
            self.paymt_lines.currency_id = self.currency_id

    @api.depends('curr_rate', 'payment_amount', 'paymt_lines.l_payment_amount', 'paymt_lines.l_local_amount')
    def _calc_local_amount(self):
        #  get payment sequence
        # self._get_default_name()
        # ************************************************************
        self.total_cr = 0
        # self.total_cr += sum(line.l_local_amount for line in self.paymt_lines)
        for i in self:
            i.local_amount = i.curr_rate * i.payment_amount
            i.total_dr = i.local_amount

        for l in self.paymt_lines:
            l.l_local_amount = l.curr_rate * l.l_payment_amount
            i.total_cr += l.l_local_amount

    @api.model
    def _default_multi_currency_policy(self):
        return self.user_has_groups('base.group_multi_currency')

    @api.onchange('payment_type')
    def _get_default_name(self):
        # print(self.env.context.get('report_name', False))
        print(self.payment_type)
        sql_query = ""
        # if self.type_id/ == 1:
        sql_query = "select max(COALESCE(payment_seq,0)) as seq from custom_account_payment where payment_type='%s'" % self.payment_type
        # else:
        #     if self.type_id == 2:
        #         sql_query = "select max(COALESCE(payment_seq,0)) from custom_account_payment where payment_type='issue'"
        # if sql_query:
        self.env.cr.execute(sql_query)
        seq = self.env.cr.fetchone()
        x = seq[0]
        if x:
            x = x + 1
            self.payment_seq = x

            # return (x)
        else:
            x = 1
            self.payment_seq = x
            # return (x)

    def _prepare_payment_moves(self):
        all_move_vals = []
        mov_vals= ''
        for payment in self:
            if payment.payment_type == 'receipt':
                l_move_name = 'PRCPT/ ' + str(self.payment_seq)
                l_account_internal_type = self.env['account.account'].search(
                    [('id', '=', payment.journal_id.default_debit_account_id.id)]).internal_type
                line_ids = []
                debit_vals = (0, 0, {
                    'name': payment.desc,
                    'amount_currency': payment.payment_amount if payment.check_multi_currency and (
                                payment.company_id.currency_id.id != payment.currency_id.id) else 0.0,
                    'currency_id': payment.currency_id.id if payment.check_multi_currency and (
                                payment.company_id.currency_id.id != payment.currency_id.id) else 0.0,
                    'company_currency_id': payment.company_id.currency_id.id,
                    'debit': payment.local_amount if payment.check_multi_currency else payment.payment_amount,
                    'credit': 0,
                    # 'balance': payment.local_amount if payment.check_multi_currency else payment.payment_amount,
                    'date': payment.payment_date,
                    'date_maturity': payment.payment_date,
                    'account_id': payment.journal_id.default_debit_account_id.id,
                    'account_internal_type': l_account_internal_type,
                    # 'parent_state': 'posted',
                    'ref': l_move_name,
                    'journal_id': payment.journal_id.id,
                    'company_id': payment.company_id.id,
                    'quantity': 1,
                    'custom_payment_line_id': payment.id,
                })
                line_ids.append(debit_vals)
                for line in payment.paymt_lines:
                    l_account_internal_type = self.env['account.account'].search(
                        [('id', '=', line.account_id.id)]).internal_type

                    credit_vals = (0, 0, {
                        'name': line.desc,
                        'amount_currency': -(line.l_payment_amount) if payment.check_multi_currency and (
                                    payment.company_id.currency_id.id != line.currency_id.id) else -0.0,
                        'currency_id': line.currency_id.id if payment.check_multi_currency and (
                                    payment.company_id.currency_id.id != line.currency_id.id) else 0.0,
                        'company_currency_id': payment.company_id.currency_id.id,
                        'debit': 0.0,
                        'credit': (line.l_local_amount) if payment.check_multi_currency else (line.l_payment_amount),
                        # 'balance': -(line.l_local_amount) if payment.check_multi_currency else -(line.l_payment_amount),
                        'date': payment.payment_date,
                        'date_maturity': payment.payment_date,
                        'account_id': line.account_id.id,
                        'account_internal_type': l_account_internal_type,
                        # 'parent_state': 'posted',
                        'ref': l_move_name,
                        'journal_id': payment.journal_id.id,
                        'company_id': payment.company_id.id,
                        'partner_id': line.partner_id.id if line.partner_id else False,
                        'quantity': 1,
                        'custom_payment_line_id': line.id,

                    })

                    line_ids.append(credit_vals, )

                mov_vals = {
                    'date': payment.payment_date,
                    'ref': 'PRCPT/ ' + str(payment.payment_seq),
                    # 'state': 'posted',
                    'type': 'entry',
                    'journal_id': payment.journal_id.id,
                    'company_id': payment.company_id.id,
                    'currency_id': payment.currency_id.id,
                    # 'amount_total': payment.payment_amount, #if payment.check_multi_currency and (payment.company_id.currency_id.id != line.currency_id.id) else payment.local_amount,
                    # 'amount_total_signed': payment.local_amount, #if payment.check_multi_currency and (payment.company_id.currency_id.id != line.currency_id.id) else payment.local_amount,
                    'invoice_user_id': payment.user_id.id,
                    'custom_payment_id': payment.id,
                    'line_ids': line_ids
                }

                print(mov_vals)

            else:
                if payment.payment_type == 'issue':
                    l_move_name = 'PISSUE/ ' + str(self.payment_seq)
                    l_account_internal_type = self.env['account.account'].search(
                        [('id', '=', payment.journal_id.default_debit_account_id.id)]).internal_type
                    line_ids = []
                    credit_vals = (0, 0, {
                        'name': payment.desc,
                        'amount_currency': -(payment.payment_amount) if payment.check_multi_currency and (
                                payment.company_id.currency_id.id != payment.currency_id.id) else -0.0,
                        'currency_id': payment.currency_id.id if payment.check_multi_currency and (
                                payment.company_id.currency_id.id != payment.currency_id.id) else 0.0,
                        'company_currency_id': payment.company_id.currency_id.id,
                        'credit': (payment.local_amount) if payment.check_multi_currency else (payment.payment_amount),
                        'debit': 0,
                        # 'balance': payment.local_amount if payment.check_multi_currency else payment.payment_amount,
                        'date': payment.payment_date,
                        'date_maturity': payment.payment_date,
                        'account_id': payment.journal_id.default_credit_account_id.id,
                        'account_internal_type': l_account_internal_type,
                        # 'parent_state': 'posted',
                        'ref': l_move_name,
                        'journal_id': payment.journal_id.id,
                        'company_id': payment.company_id.id,
                        'quantity': 1,
                        'custom_payment_line_id': payment.id,

                    })
                    line_ids.append(credit_vals)
                    for line in payment.paymt_lines:
                        l_account_internal_type = self.env['account.account'].search(
                            [('id', '=', line.account_id.id)]).internal_type

                        debit_vals = (0, 0, {
                            'name': line.desc,
                            'amount_currency': (line.l_payment_amount) if payment.check_multi_currency and (
                                    payment.company_id.currency_id.id != line.currency_id.id) else 0.0,
                            'currency_id': line.currency_id.id if payment.check_multi_currency and (
                                    payment.company_id.currency_id.id != line.currency_id.id) else 0.0,
                            'company_currency_id': payment.company_id.currency_id.id,
                            'debit': (line.l_local_amount) if payment.check_multi_currency else (line.l_payment_amount),
                            'credit': 0.0,
                            # 'balance': -(line.l_local_amount) if payment.check_multi_currency else -(line.l_payment_amount),
                            'date': payment.payment_date,
                            'date_maturity': payment.payment_date,
                            'account_id': line.account_id.id,
                            'account_internal_type': l_account_internal_type,
                            # 'parent_state': 'posted',
                            'ref': l_move_name,
                            'journal_id': payment.journal_id.id,
                            'company_id': payment.company_id.id,
                            'partner_id': line.partner_id.id if line.partner_id else False,
                            'quantity': 1,
                            'custom_payment_line_id': line.id,

                        })

                        line_ids.append(debit_vals, )

                    mov_vals = {
                        'date': payment.payment_date,
                        'ref': 'PISSUE/ ' + str(payment.payment_seq),
                        # 'state': "posted" if payment.check_auto_posted else "Draft",
                        'type': 'entry',
                        'journal_id': payment.journal_id.id,
                        'company_id': payment.company_id.id,
                        'currency_id': payment.currency_id.id,
                        # 'amount_total': payment.payment_amount, #if payment.check_multi_currency and (payment.company_id.currency_id.id != line.currency_id.id) else payment.local_amount,
                        # 'amount_total_signed': payment.local_amount, #if payment.check_multi_currency and (payment.company_id.currency_id.id != line.currency_id.id) else payment.local_amount,
                        'invoice_user_id': payment.user_id.id,
                        'custom_payment_id': payment.id,
                        'line_ids': line_ids
                    }

                    print(mov_vals)

        return mov_vals

    def _update_payment_moves(self,moves):
        all_move_vals = []
        mov_vals= ''
        for payment in self:
            if payment.payment_type == 'receipt':
                l_move_name = 'PRCPT/ ' + str(self.payment_seq)
                l_account_internal_type = self.env['account.account'].search(
                    [('id', '=', payment.journal_id.default_debit_account_id.id)]).internal_type
                line_ids = []
                debit_vals = (0, 0, {
                    'name': payment.desc,
                    'amount_currency': payment.payment_amount if payment.check_multi_currency and (
                                payment.company_id.currency_id.id != payment.currency_id.id) else 0.0,
                    'currency_id': payment.currency_id.id if payment.check_multi_currency and (
                                payment.company_id.currency_id.id != payment.currency_id.id) else 0.0,
                    'company_currency_id': payment.company_id.currency_id.id,
                    'debit': payment.local_amount if payment.check_multi_currency else payment.payment_amount,
                    'credit': 0,
                    # 'balance': payment.local_amount if payment.check_multi_currency else payment.payment_amount,
                    'date': payment.payment_date,
                    'date_maturity': payment.payment_date,
                    'account_id': payment.journal_id.default_debit_account_id.id,
                    'account_internal_type': l_account_internal_type,
                    # 'parent_state': 'posted',
                    'ref': l_move_name,
                    'journal_id': payment.journal_id.id,
                    'company_id': payment.company_id.id,
                    'quantity': 1,
                    'custom_payment_line_id': payment.id,
                })
                line_ids.append(debit_vals)
                for line in payment.paymt_lines:
                    l_account_internal_type = self.env['account.account'].search(
                        [('id', '=', line.account_id.id)]).internal_type

                    credit_vals = (0, 0, {
                        'name': line.desc,
                        'amount_currency': -(line.l_payment_amount) if payment.check_multi_currency and (
                                    payment.company_id.currency_id.id != line.currency_id.id) else -0.0,
                        'currency_id': line.currency_id.id if payment.check_multi_currency and (
                                    payment.company_id.currency_id.id != line.currency_id.id) else 0.0,
                        'company_currency_id': payment.company_id.currency_id.id,
                        'debit': 0.0,
                        'credit': (line.l_local_amount) if payment.check_multi_currency else (line.l_payment_amount),
                        # 'balance': -(line.l_local_amount) if payment.check_multi_currency else -(line.l_payment_amount),
                        'date': payment.payment_date,
                        'date_maturity': payment.payment_date,
                        'account_id': line.account_id.id,
                        'account_internal_type': l_account_internal_type,
                        # 'parent_state': 'posted',
                        'ref': l_move_name,
                        'journal_id': payment.journal_id.id,
                        'company_id': payment.company_id.id,
                        'partner_id': line.partner_id.id if line.partner_id else False,
                        'quantity': 1,
                        'custom_payment_line_id': line.id,

                    })

                    line_ids.append(credit_vals, )


                # for line_inv in moves.line_ids:
                #     print("line_inv",line_inv)
                moves.write({'line_ids': [(5, )]})

                moves.write({
                    'date': payment.payment_date,
                    'ref': 'PRCPT/ ' + str(payment.payment_seq),
                    # 'state': 'posted',
                    'type': 'entry',
                    'journal_id': payment.journal_id.id,
                    'company_id': payment.company_id.id,
                    'currency_id': payment.currency_id.id,
                    # 'amount_total': payment.payment_amount, #if payment.check_multi_currency and (payment.company_id.currency_id.id != line.currency_id.id) else payment.local_amount,
                    # 'amount_total_signed': payment.local_amount, #if payment.check_multi_currency and (payment.company_id.currency_id.id != line.currency_id.id) else payment.local_amount,
                    'invoice_user_id': payment.user_id.id,
                    'custom_payment_id': payment.id,
                    'line_ids': line_ids
                    })

                print(mov_vals)

            else:
                if payment.payment_type == 'issue':
                    l_move_name = 'PISSUE/ ' + str(self.payment_seq)
                    l_account_internal_type = self.env['account.account'].search(
                        [('id', '=', payment.journal_id.default_debit_account_id.id)]).internal_type
                    line_ids = []
                    credit_vals = (0, 0, {
                        'name': payment.desc,
                        'amount_currency': -(payment.payment_amount) if payment.check_multi_currency and (
                                payment.company_id.currency_id.id != payment.currency_id.id) else -0.0,
                        'currency_id': payment.currency_id.id if payment.check_multi_currency and (
                                payment.company_id.currency_id.id != payment.currency_id.id) else 0.0,
                        'company_currency_id': payment.company_id.currency_id.id,
                        'credit': (payment.local_amount) if payment.check_multi_currency else (payment.payment_amount),
                        'debit': 0,
                        # 'balance': payment.local_amount if payment.check_multi_currency else payment.payment_amount,
                        'date': payment.payment_date,
                        'date_maturity': payment.payment_date,
                        'account_id': payment.journal_id.default_credit_account_id.id,
                        'account_internal_type': l_account_internal_type,
                        # 'parent_state': 'posted',
                        'ref': l_move_name,
                        'journal_id': payment.journal_id.id,
                        'company_id': payment.company_id.id,
                        'quantity': 1,
                        'custom_payment_line_id': payment.id,

                    })
                    line_ids.append(credit_vals)
                    for line in payment.paymt_lines:
                        l_account_internal_type = self.env['account.account'].search(
                            [('id', '=', line.account_id.id)]).internal_type

                        debit_vals = (0, 0, {
                            'name': line.desc,
                            'amount_currency': (line.l_payment_amount) if payment.check_multi_currency and (
                                    payment.company_id.currency_id.id != line.currency_id.id) else 0.0,
                            'currency_id': line.currency_id.id if payment.check_multi_currency and (
                                    payment.company_id.currency_id.id != line.currency_id.id) else 0.0,
                            'company_currency_id': payment.company_id.currency_id.id,
                            'debit': (line.l_local_amount) if payment.check_multi_currency else (line.l_payment_amount),
                            'credit': 0.0,
                            # 'balance': -(line.l_local_amount) if payment.check_multi_currency else -(line.l_payment_amount),
                            'date': payment.payment_date,
                            'date_maturity': payment.payment_date,
                            'account_id': line.account_id.id,
                            'account_internal_type': l_account_internal_type,
                            # 'parent_state': 'posted',
                            'ref': l_move_name,
                            'journal_id': payment.journal_id.id,
                            'company_id': payment.company_id.id,
                            'partner_id': line.partner_id.id if line.partner_id else False,
                            'quantity': 1,
                            'custom_payment_line_id': line.id,

                        })

                        line_ids.append(debit_vals, )

                    for line_inv in moves.line_ids:
                        moves.write({'line_ids': [(2, line_inv.id)]})

                    moves.write({
                        'date': payment.payment_date,
                        'ref': 'PISSUE/ ' + str(payment.payment_seq),
                        # 'state': "posted" if payment.check_auto_posted else "Draft",
                        'type': 'entry',
                        'journal_id': payment.journal_id.id,
                        'company_id': payment.company_id.id,
                        'currency_id': payment.currency_id.id,
                        # 'amount_total': payment.payment_amount, #if payment.check_multi_currency and (payment.company_id.currency_id.id != line.currency_id.id) else payment.local_amount,
                        # 'amount_total_signed': payment.local_amount, #if payment.check_multi_currency and (payment.company_id.currency_id.id != line.currency_id.id) else payment.local_amount,
                        'invoice_user_id': payment.user_id.id,
                        'custom_payment_id': payment.id,
                        'line_ids': line_ids
                        })

                    print(mov_vals)

        return mov_vals


    def custom_post(self):
        for rec in self:
            moves =''
            if rec.payment_state != 'draft':
                raise ValidationError("Only a draft payment can be posted.")

            # self.env.cr.execute(
            #     "select count(id) as branch from account_move b where custom_payment_id=%s" % rec.id)
            # check_already_payment_in_gl = self.env.cr.fetchone()
            #
            # print(check_already_payment_in_gl[0])
            # if check_already_payment_in_gl[0]:
            #     moves = self.env['account.move'].search([('custom_payment_id','=', rec.id)])
            #     move_lines = rec._prepare_payment_moves()
            #     print(move_lines)
            #     moves.clear(['line_ids'])
            #     moves.write({'line_ids': move_lines['line_ids']})

            else:
                moves = self.env['account.move'].search([('custom_payment_id', '=', self.id)])
                if moves:
                    rec._update_payment_moves(moves)

                else:
                    moves = self.env['account.move'].create(rec._prepare_payment_moves())

            if self.check_auto_posted:
                moves.action_post()
                if rec.account_move_seq:
                    moves.write({'name': rec.account_move_seq })
                else:
                    rec.write(({'account_move_seq': moves.name}))
            rec.write({'payment_state': 'posted'})

        return True

    def action_draft(self):
        check_moves_aval = self.env['account.move'].search([('custom_payment_id', '=', self.id)])
        if check_moves_aval:
            moves = self.env['account.move'].search([('custom_payment_id', '=', self.id)])
            if moves:
                moves.button_draft()
                if moves.state =='posted':
                    raise ValidationError("لا يمكن الالغاء بسبب تم ترحل السند من الحسابات مسبقا")

                elif moves.name == '/' or moves.name is None or moves.name == False or moves.name == '':
                    moves.unlink()
                else:
                    moves.line_ids.unlink()

                self.write({'payment_state': 'draft'})
            else:
                raise ValidationError("لا يمكن الالغاء بسبب تم ترحل السند من الحسابات مسبقا")
        else:
            self.write({'payment_state': 'draft'})

    def unlink(self):
        for rec in self:
            if rec.payment_state == 'posted':
                raise ValidationError("You cannot delete a payment that is already posted.")
        return super(custom_payment, self).unlink()

    @api.constrains('payment_seq', 'total_dr', 'total_cr', 'paymt_lines', 'payment_amount', 'local_amount',
                    'check_multi_currency')
    def _check_seq(self):
        global x
        x = 0
        if self.payment_type == 'receipt':
            seqs = self.env['custom.account.payment'].search([('payment_type', '=', self.payment_type)])
            for i in seqs:
                if int(self.payment_seq) == int(i.payment_seq):
                    x = x + 1

            print(self.payment_type)

            if x > 1:
                raise ValidationError(
                    "-------Exists ! Already Receipt SEQ exists in this NUMBER : %s No. of duplicate %s" % (
                        self.payment_seq, x))
        else:
            if self.payment_type == 'issue':
                seqs = self.env['custom.account.payment'].search([('payment_type', '=', self.payment_type)])
                for i in seqs:
                    if int(self.payment_seq) == int(i.payment_seq):
                        x = x + 1

                print(self.payment_type)

                if x > 1:
                    raise ValidationError(
                        "-------Exists ! Already Issue SEQ exists in this NUMBER : %s No. of duplicate %s" % (
                            self.payment_seq, x))

        if not self.paymt_lines:
            raise ValidationError("لا يمكن الحفظ يجب ادخال حسابات سند القبض")
        # #
        # for i in self:
        #     i.total_dr = i.payment_amount * i.curr_rate
        #     i.local_amount = i.payment_amount * i.curr_rate
        #
        #
        # self.total_cr = sum(l.l_local_amount for l in self.paymt_lines)
        print("self.total_cr",self.total_cr)
        print("self.total_dr",self.total_dr)


        if (round(self.total_cr,2) != round(self.total_dr,2)) or ((round(self.total_cr,2) == 0) or (round(self.total_dr,2) == 0)):
            raise ValidationError("لا يمكن الحفظ الارصدة غير متزنة")

        if not self.check_multi_currency and (self.payment_amount != self.local_amount):
            raise ValidationError(
                "لا يمكن الحفظ بسبب مبلغ السند لا يساوي مبلغ المعادل لعملة المؤسسة .. قد يكون السبب السند تم انشاءة في تعدد العملات..يجب حذفه وانشاءة من جديد ")

        if self.paymt_lines.partner_id.ids:
            # select = []
            # for rec in self.paymt_lines.partner_id.ids:
            #     select.append(rec[0])
            #
            # print(select)

            check_partner = 0
            for line in self.paymt_lines:
                for rec in line.partner_id:

                    if line.account_id.id not in (
                    rec.property_account_receivable_id.id, rec.property_account_payable_id.id):
                        check_partner = 1
            if check_partner:
                raise ValidationError(
                    "رقم الحساب يجب ان يكون من حسابات الشريك حساب العملاء او حساب الموردين")

        if self.paymt_lines:
            partner_accounts = self.env['res.partner'].search([])
            check_account = 0
            for line in self.paymt_lines:
                print(line.account_id.id)
                print(partner_accounts.property_account_receivable_id.ids)
                print(partner_accounts.property_account_payable_id.ids)
                if line.account_id.id in partner_accounts.property_account_receivable_id.ids and not line.partner_id:
                    check_account = 1
                if line.account_id.id in partner_accounts.property_account_payable_id.ids and not line.partner_id:
                    check_account = 1

            if check_account:
                raise ValidationError(
                    "تنبيه: عند استخدام حسابات اللشركاء يجب تحديد الشريك لذا لا يمكن الاستمرار")
   
    def call_entry(self):
        for rec in self:
            action = self.env.ref('account.action_move_journal_line')
            result = action.read()[0]
            result.pop('id', None)
            result['context'] = {}
            result['domain'] = [('custom_payment_id', '=', rec.id), ('type', '=', 'entry')]
            return result

class custom_payment_line(models.Model):
    _name = 'custom.account.payment.line'
    _description = 'Accounting Payment Line'
    account_id = fields.Many2one('account.account', string='Account', required=True)
    tax_line_id = fields.Many2one('custom.account.payment.line',)
    tax_id = fields.Many2one('account.tax')
    partner_id = fields.Many2one('res.partner')

    l_payment_amount = fields.Float('Payment amount', required=True)
    curr_rate = fields.Float(string='Currency rate', required=True, default=1, readonly=True)
    l_local_amount = fields.Float(string='Local amount', required=True)
    currency_id = fields.Many2one('res.currency', domain=[('active', '=', True)],
                                  default=lambda self: self.env.company.currency_id, readonly=True, required=True)
    desc = fields.Char(string='Description', required=True)
    pymt_id = fields.Many2one('custom.account.payment', string='id')

    @api.onchange('pymt_id', 'account_id')
    def get_rate(self):
        self.currency_id = self.pymt_id.currency_id
        self.curr_rate = self.pymt_id.curr_rate
   
    @api.onchange('account_id','l_payment_amount')
    def calc_account_tax_amount(self):
        for rec in self:
            if rec.account_id:
                if rec.account_id.tax_ids:
                    if rec.l_payment_amount:
                        if not rec.tax_line_id:
                            tax = self.env['account.tax'].search([('id','in',rec.account_id.tax_ids.ids)],limit=1)
                            if tax:
                                amount_tax =  rec.l_payment_amount * (tax.amount/100)
                                tax_name =   (tax.name)
                                tax_account_id = tax.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax')[:1].account_id.id
                                if tax_account_id:
                                    line = self.env['custom.account.payment.line'].create({
                                        'account_id':tax_account_id,
                                        'desc': tax_name,
                                        'l_payment_amount':amount_tax,
                                        'currency_id':rec.pymt_id.currency_id.id,
                                        'curr_rate':rec.pymt_id.curr_rate,
                                        'pymt_id': rec.pymt_id.id,
                                        'l_local_amount': rec.pymt_id.curr_rate * amount_tax,

                                        })
                                    rec.write({'tax_line_id': line.id})
                                    rec.write({'tax_id': tax.id})
                                    rec.calc_local_amount()
                        else:
                            amount_tax =  rec.l_payment_amount * (rec.tax_id.amount/100)
                            rec.tax_line_id.write({'l_payment_amount': amount_tax})
                            rec.tax_line_id.write({'l_local_amount':  rec.pymt_id.curr_rate * amount_tax})
                            rec.calc_local_amount()
                    else:
                        rec.tax_line_id.unlink()


                                
 





    @api.onchange('account_id')
    def get_partner(self):
        if self.account_id:
            partner = self.env['res.partner'].search(['|', ('property_account_receivable_id', '=', self.account_id.id),
                                                      ('property_account_payable_id', '=', self.account_id.id)])
            select = []
            if partner:
                for i in partner:
                    select.append(i.id)
                print(select)
                return {'domain': {'partner_id': [('id', 'in', select)]}}
            else:
                return {'domain': {'partner_id': [('id', 'in', False)]}}

    @api.onchange('curr_rate', 'l_payment_amount')
    def calc_local_amount(self):
        # if self.curr_rate > 0 and self.foreign_amt > 0:

        for i in self:
            i.l_local_amount = i.curr_rate * i.l_payment_amount

    def init(self):
        self._cr.execute("""update account_move_line set partner_id=a.p_partner_id from  (select  p_ref ,account_id as p_account_id,
                                partner_id as p_partner_id,
                                p_debit,p_credit from (
                                    select ('P'||case when payment_type='receipt' then 'RCPT' ELSE 'ISSUE' end ||'/ '||payment_seq) as p_ref,
                                        case when payment_type='receipt' then l_payment_amount ELSE 0 end as p_credit,
                                        case when payment_type='issue' then l_payment_amount ELSE 0 end as p_debit,

                                        *

                                        from custom_account_payment a,custom_account_payment_line b
                                    where a.id=b.pymt_id
                                        ) x) a
                                        where a.p_ref=ref and a.p_account_id=account_id and debit=p_debit and credit=p_credit
                                        and partner_id is null""")
