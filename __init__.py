#This file is part of the nodux_account_postdated_check module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.

from trytond.pool import Pool
from .postdated_check import *
from .reconciliation import *
def register():
    Pool.register(
        AccountPostDateCheck,
        AccountBankReconciliation,
        ReconciliationStart,
        module='nodux_account_bank_reconciliation', type_='model')
    Pool.register(
        Reconciliation,
        module='nodux_account_bank_reconciliation', type_='wizard')
