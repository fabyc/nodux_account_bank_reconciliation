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

class AccountPostDateCheck():
    __metaclass__ = PoolMeta
    __name__ = 'account.postdated'
    _rec_name = 'number'

    @classmethod
    def __setup__(cls):
        super(AccountPostDateCheck, cls).__setup__()

    def create_lines_reconcile(self):
        pool = Pool()
        Reconciled = pool.get('account.reconciliation')
        reconciled = Reconciled()

        for line in self.lines:
            reconciled.amount = line.amount
            reconciled.conciliar = False
            reconciled.account = line.account_new.id
            reconciled.state = 'draft'
            reconciled.date = line.date
            reconciled.save()

    @classmethod
    @ModelView.button
    def post(cls, postdateds):
        for postdated in postdateds:
            postdated.set_number()
            move_lines = postdated.prepare_lines()
            postdated.deposit(move_lines)
            postdated.create_lines_reconcile()
        cls.write(postdateds, {'state': 'posted'})
