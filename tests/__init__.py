# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

try:
    from trytond.modules.contract_discount.tests.test_contract_discount import suite
except ImportError:
    from .test_contract_discount import suite

__all__ = ['suite']
