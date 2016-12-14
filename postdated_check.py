# -*- coding: utf-8 -*-
#This file is part of the nodux_account_postdated_check module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
from decimal import Decimal
from trytond.model import ModelSingleton, ModelView, ModelSQL, fields
from trytond.transaction import Transaction
from trytond.pyson import Eval, In
from trytond.pool import Pool, PoolMeta
from trytond.report import Report
import pytz
from datetime import datetime,timedelta
import time

conversor = None
try:
    from numword import numword_es
    conversor = numword_es.NumWordES()
except:
    print("Warning: Does not possible import numword module!")
    print("Please install it...!")


__all__ = ['AccountPostDateCheck']
__metaclass__ = PoolMeta

class AccountPostDateCheck():
    'Account Post Date Check'
    __name__ = 'account.postdated'
    _rec_name = 'number'

    @classmethod
    def __setup__(cls):
        super(AccountPostDateCheck, cls).__setup__()

    def create_lines_reconcile(self):
        pool = Pool()
        Reconciled = pool.get('account.reconciliation')
        AllReconciled = pool.get('account.reconciliation_all')
        Bank = pool.get('bank')
        reconciled = Reconciled()
        allreconciled = AllReconciled()
        amount_total = Decimal(0.0)
        
        all_r = None
        for line in self.lines:
            account = line.account_new.id
        banks = Bank.search([('account_expense', '=', account)])
        if banks:
            for bank in banks:
                if bank.nro_cuenta_bancaria:
                    nro_cuenta_bancaria = bank.nro_cuenta_bancaria
                else:
                    self.raise_user_error('Configure el numero de cuenta bancaria')
                if bank.party.name:
                    name_bank = bank.party.name
                else:
                    self.raise_user_error('Configure el nombre del Banco')
        else:
            self.raise_user_error('Configure los datos del Banco')

        all_rs = AllReconciled.search([('account_bank', '=', nro_cuenta_bancaria)])

        if all_rs:
            for a_r in all_rs:
                allreconciled = a_r
        else:
            allreconciled.name_bank = name_bank
            allreconciled.account_bank = nro_cuenta_bancaria
            allreconciled.save()


        for line in self.lines:
            amount_total += line.amount
            reconciled.bank_account_ref = allreconciled.id
            reconciled.amount = line.amount
            reconciled.conciliar = False
            reconciled.account = line.account_new.id
            reconciled.state = 'draft'
            reconciled.date = line.date
            reconciled.expired = line.date_expire
            reconciled.party = self.party
            reconciled.ch_num = line.num_check
            reconciled.bank_account = line.num_account
            reconciled.save()

        allreconciled.libro_credito = allreconciled.libro_credito  + amount_total
        allreconciled.libro_balance = (allreconciled.libro_inicial + allreconciled.libro_credito)-allreconciled.libro_debito
        allreconciled.save()

    @classmethod
    @ModelView.button
    def post(cls, postdateds):
        for postdated in postdateds:
            postdated.set_number()
            move_lines = postdated.prepare_lines()
            postdated.deposit(move_lines)
            postdated.create_lines_reconcile()
        cls.write(postdateds, {'state': 'posted'})
