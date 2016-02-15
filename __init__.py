# This file is part of the contract_rcc module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool
from .contract import *


def register():
    Pool.register(
        Contract,
        ContractLine,
        ContractConsumption,
        module='contract_rcc', type_='model')
