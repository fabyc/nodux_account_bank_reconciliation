# -*- coding: utf-8 -*-
#This file is part of the nodux_account_bank_reconciliation module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
from decimal import Decimal
from trytond.model import ModelSingleton, ModelView, ModelSQL, fields
from trytond.transaction import Transaction
from trytond.pyson import Eval, In
from trytond.pool import Pool
from trytond.report import Report
import pytz
from datetime import datetime,timedelta
import time
from trytond.wizard import (Wizard, StateView, StateAction, StateTransition,
    Button)

conversor = None
try:
    from numword import numword_es
    conversor = numword_es.NumWordES()
except:
    print("Warning: Does not possible import numword module!")
    print("Please install it...!")


__all__ = [ 'AccountBankReconciliation', 'ReconciliationStart', 'Reconciliation',
        'OpenReconciliationStart', 'OpenReconciliation','ReconciliationReport',
        'OpenSummaryReconciliationStart', 'OpenSummaryReconciliation',
        'SummaryReconciliationReport']

_STATES = {
    'readonly': In(Eval('state'), ['reconciled']),
}

class AccountBankReconciliation(ModelSQL, ModelView):
    'Account Bank Reconciliation'
    __name__ = 'account.reconciliation'

    date = fields.Date('Date', required=True, states=_STATES)
    currency = fields.Many2One('currency.currency', 'Currency', states=_STATES)
    company = fields.Many2One('company.company', 'Company', states=_STATES)
    amount  = fields.Numeric('Valor', states=_STATES)
    conciliar = fields.Boolean('Conciliar', states=_STATES)
    account = fields.Many2One('account.account', 'Cuenta', states=_STATES)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('reconciled', 'Conciliado'),
        ], 'Estado', select=True, readonly=True)
    expired = fields.Date('Expired Date', required=True, states=_STATES)
    party = fields.Many2One('party.party', 'Party')
    ch_num = fields.Char('Check num')
    bank_account = fields.Char('Number bank account')

    @classmethod
    def __setup__(cls):
        super(AccountBankReconciliation, cls).__setup__()
        cls._error_messages.update({
            'delete_reconcile': 'No puede eliminiar una conciliacion bancaria!',
        })
        cls._buttons.update({
                'reconcile': {
                    'invisible': Eval('state') == 'reconciled',
                    },
                })

    @staticmethod
    def default_state():
        return 'draft'

    @staticmethod
    def default_currency():
        Company = Pool().get('company.company')
        company_id = Transaction().context.get('company')
        if company_id:
            return Company(company_id).currency.id

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    @classmethod
    def delete(cls, reconcileds):
        if not reconcileds:
            return True
        for reconciled in reconcileds:
            if reconciled.state == 'reconciled':
                cls.raise_user_error('delete_reconcile')
        return super(AccountBankReconciliation, cls).delete(reconcileds)

    @classmethod
    @ModelView.button
    def reconcile(cls, reconcileds):
        for reconciled in reconcileds:
            #postdated.set_number()
            if reconciled.conciliar == True:
                pass
            else:
                reconciled.write([reconciled],{ 'conciliar': True})
        cls.write(reconcileds, {'state': 'reconciled'})

class ReconciliationStart(ModelView):
    'Reconciliation Start'
    __name__ = 'account.reconciliation.start'


class Reconciliation(Wizard):
    'Reconciliation'
    __name__ = 'account.all.reconciliation'

    start = StateView('account.reconciliation.start',
        'nodux_account_bank_reconciliation.reconciliation_start_view_form', [
        Button('Cancel', 'end', 'tryton-cancel'),
        Button('Conciliar', 'accept', 'tryton-ok', default=True),
        ])
    accept = StateTransition()

    def transition_accept(self):
        Reconcileds = Pool().get('account.reconciliation')
        reconcileds = Reconcileds.browse(Transaction().context['active_ids'])

        for reconciled in reconcileds:
            if reconciled.conciliar == True:
                pass

            else:
                reconciled.write([reconciled],{ 'conciliar': True})
                reconciled.write([reconciled], {'state': 'reconciled'})
        return 'end'

class OpenReconciliationStart(ModelView):
    'Open Reconciliation Start'
    __name__ = 'nodux_account_bank_reconciliation.print_reconciliation.start'

    company = fields.Many2One('company.company', 'Company', required=True)
    fecha = fields.Date('Fecha de conciliacion', help='Fecha de conciliacion para reporte')
    start_period = fields.Many2One('account.period', 'Period')
    account = fields.Many2One('bank.account.number', 'Bank account')

    @staticmethod
    def default_company():
        return Transaction().context.get('company')


    @staticmethod
    def default_fecha():
        Date = Pool().get('ir.date')
        date = Date.today()
        return date

class OpenReconciliation(Wizard):
    'Open Reconciliation'
    __name__ = 'nodux_account_bank_reconciliation.print_reconciliation'

    start = StateView('nodux_account_bank_reconciliation.print_reconciliation.start',
        'nodux_account_bank_reconciliation.print_reconciliation_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-ok', default=True),
            ])
    print_ = StateAction('nodux_account_bank_reconciliation.report_account_reconciliation')

    def do_print_(self, action):
        if self.start.fecha:
            fecha = self.start.fecha
        if self.start.company:
            company = self.start.company

        data = {
            'fecha': fecha,
            'company': company.id,
            }
        return action, data

    def transition_print_(self):
        return 'end'


class ReconciliationReport(Report):
    'Reconciliation Report'
    __name__ = 'account.reconciliation.report'

    @classmethod
    def parse(cls, report, objects, data, localcontext=None):
        total = Decimal(0.0)
        Company = Pool().get('company.company')
        Reconciliation = Pool().get('account.reconciliation')
        company = Company(data['company'])
        company_id = Transaction().context.get('company')
        company = Company(company_id)
        fecha = data['fecha']
        reconciliations = Reconciliation.search([('date','=', fecha)])
        if company.timezone:
            timezone = pytz.timezone(company.timezone)
            dt = datetime.now()
            hora = datetime.astimezone(dt.replace(tzinfo=pytz.utc), timezone)
        for r in reconciliations:
            total += r.amount

        localcontext['company'] = company
        localcontext['hora'] = hora.strftime('%H:%M:%S')
        localcontext['fecha'] = hora.strftime('%d/%m/%Y')
        localcontext['reconciliations'] = reconciliations
        localcontext['total'] = total
        new_objs = []

        return super(ReconciliationReport, cls).parse(report,
                new_objs, data, localcontext)

class OpenSummaryReconciliationStart(ModelView):
    'Open Summary Reconciliation Start'
    __name__ = 'nodux_account_bank_reconciliation.print_summary_reconciliation.start'

    company = fields.Many2One('company.company', 'Company', required=True)
    fecha = fields.Date('Fecha de conciliacion', help='Fecha de conciliacion para reporte')
    start_period = fields.Many2One('account.period', 'Period')
    account = fields.Many2One('bank.account.number', 'Bank account')

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    @staticmethod
    def default_fecha():
        Date = Pool().get('ir.date')
        date = Date.today()
        return date

class OpenSummaryReconciliation(Wizard):
    'Open Summary Reconciliation'
    __name__ = 'nodux_account_bank_reconciliation.print_summary_reconciliation'

    start = StateView('nodux_account_bank_reconciliation.print_summary_reconciliation.start',
        'nodux_account_bank_reconciliation.print_summary_reconciliation_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-ok', default=True),
            ])
    print_ = StateAction('nodux_account_bank_reconciliation.report_account_summary_reconciliation')

    def do_print_(self, action):
        if self.start.fecha:
            fecha = self.start.fecha
        if self.start.company:
            company = self.start.company

        data = {
            'fecha': fecha,
            'company': company.id,
            }
        return action, data

    def transition_print_(self):
        return 'end'


class SummaryReconciliationReport(Report):
    'Summary Reconciliation Report'
    __name__  = 'account.summary_reconciliation.report'

    @classmethod
    def parse(cls, report, objects, data, localcontext=None):
        total = Decimal(0.0)
        Company = Pool().get('company.company')
        Reconciliation = Pool().get('account.reconciliation')
        company = Company(data['company'])
        company_id = Transaction().context.get('company')
        company = Company(company_id)
        fecha = data['fecha']
        reconciliations = Reconciliation.search([('date','=', fecha)])
        if company.timezone:
            timezone = pytz.timezone(company.timezone)
            dt = datetime.now()
            hora = datetime.astimezone(dt.replace(tzinfo=pytz.utc), timezone)
        for r in reconciliations:
            total += r.amount

        localcontext['company'] = company
        localcontext['hora'] = hora.strftime('%H:%M:%S')
        localcontext['fecha'] = hora.strftime('%d/%m/%Y')
        localcontext['reconciliations'] = reconciliations
        localcontext['total'] = total
        new_objs = []

        return super(SummaryReconciliationReport, cls).parse(report,
                new_objs, data, localcontext)
