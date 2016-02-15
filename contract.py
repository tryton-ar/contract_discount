#! -*- coding: utf8 -*-
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval

__all__ = ['Contract', 'ContractConsumption', 'ContractLine']
__metaclass__ = PoolMeta


class Contract:
    'Contract'
    __name__ = 'contract'


class ContractLine:
    'Contract'
    __name__ = 'contract.line'


class ContractConsumption:
    'Contract Consumption'
    __name__ = 'contract.consumption'

    @classmethod
    def _get_invoice(cls, keys):
        invoice = super(ContractConsumption, cls)._get_invoice(keys)
        #contract = dict(keys)['contract']
        #if contract.paymode:
        #    invoice.paymode = contract.paymode
        #if contract.client_number:
        #    invoice.client_identifier = contract.client_number
        #if contract.contract_address:
        #    invoice.invoice_address = contract.contract_address

        return invoice
