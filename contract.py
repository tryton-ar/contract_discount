#! -*- coding: utf8 -*-
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.modules.product import price_digits
from trytond.config import config as config_
from decimal import Decimal

__all__ = ['Contract', 'ContractConsumption', 'ContractLine']
__metaclass__ = PoolMeta

DISCOUNT_DIGITS = config_.getint('product', 'discount_decimal', default=4)


class Contract:
    'Contract'
    __name__ = 'contract'

    contract_discount = fields.Numeric('Contract Discount',
        digits=(16, DISCOUNT_DIGITS), states={
            'readonly': Eval('state') != 'draft',
            }, depends=['state'],
        help='This discount will be applied in all lines after their own '
        'discount.')

    @classmethod
    def __setup__(cls):
        super(Contract, cls).__setup__()
        if not cls.lines.context:
            cls.lines.context = {}
        cls.lines.context['contract_discount'] = Eval('contract_discount')
        cls.lines.depends.append('contract_discount')

    @staticmethod
    def default_contract_discount():
        return Decimal(0)

    @classmethod
    def write(cls, *args):
        actions = iter(args)
        contracts_todo = []
        for contracts, _ in zip(actions, actions):
            contracts_todo.extend(contracts)
        super(Contract, cls).write(*args)
        cls.apply_discount_to_lines(contracts_todo)

    @classmethod
    def create(cls, vlist):
        contracts = super(Contract, cls).create(vlist)
        cls.apply_discount_to_lines(contracts)
        return contracts

    @classmethod
    def apply_discount_to_lines(cls, contracts):
        Line = Pool().get('contract.line')
        to_write = []
        for contract in contracts:
            for line in contract.lines:
                old_unit_price = line.unit_price
                line.update_prices()
                if old_unit_price != line.unit_price:
                    to_write.append(line)
        if to_write:
            Line.save(to_write)


class ContractLine:
    'Contract'
    __name__ = 'contract.line'

    gross_unit_price = fields.Numeric('Gross Price', digits=price_digits,
        depends=['type'])
    gross_unit_price_wo_round = fields.Numeric('Gross Price without rounding',
        digits=(16, price_digits[1] + DISCOUNT_DIGITS), readonly=True)
    discount = fields.Numeric('Discount', digits=(16, DISCOUNT_DIGITS),
        depends=['type'])

    @classmethod
    def __setup__(cls):
        super(ContractLine, cls).__setup__()
        cls.unit_price.states['readonly'] = True
        cls.unit_price.digits = (20, price_digits[1] + DISCOUNT_DIGITS)

    def update_prices(self):
        unit_price = None
        gross_unit_price = gross_unit_price_wo_round = self.gross_unit_price
        contract_discount = Transaction().context.get('contract_discount')

        if contract_discount is None:
            if (hasattr(self, 'contract') and
                    hasattr(self.contract, 'contract_discount')):
                contract_discount = (self.contract.contract_discount or
                    Decimal(0))
            else:
                contract_discount = Decimal(0)
        if self.gross_unit_price is not None and (self.discount is not None or
                contract_discount is not None):
            unit_price = self.gross_unit_price
            if self.discount:
                unit_price *= (1 - self.discount)
            if contract_discount:
                unit_price *= (1 - contract_discount)

            if self.discount and contract_discount:
                discount = (self.discount + contract_discount -
                    self.discount * contract_discount)
                if discount != 1:
                    gross_unit_price_wo_round = unit_price / (1 - discount)
            elif self.discount and self.discount != 1:
                gross_unit_price_wo_round = unit_price / (1 - self.discount)
            elif contract_discount and contract_discount != 1:
                gross_unit_price_wo_round = \
                    unit_price / (1 - contract_discount)

            digits = self.__class__.unit_price.digits[1]
            unit_price = unit_price.quantize(Decimal(str(10.0 ** -digits)))

            digits = self.__class__.gross_unit_price.digits[1]
            gross_unit_price = gross_unit_price_wo_round.quantize(
                Decimal(str(10.0 ** -digits)))

        self.gross_unit_price = gross_unit_price
        self.gross_unit_price_wo_round = gross_unit_price_wo_round
        self.unit_price = unit_price

    @fields.depends('gross_unit_price', 'discount',
        '_parent_sale.sale_discount')
    def on_change_gross_unit_price(self):
        return self.update_prices()

    @staticmethod
    def default_discount():
        return Decimal(0)

    @fields.depends('gross_unit_price', 'discount',
        '_parent_sale.sale_discount')
    def on_change_discount(self):
        return self.update_prices()

    @fields.depends('discount', 'service', 'unit_price', 'description')
    def on_change_service(self):
        super(ContractLine, self).on_change_service()
        self.gross_unit_price = self.unit_price
        self.discount = Decimal(0)

        if self.unit_price:
            self.gross_unit_price = self.unit_price
            self.update_prices()

    @classmethod
    def create(cls, vlist):
        Contract = Pool().get('contract')
        vlist = [x.copy() for x in vlist]
        for vals in vlist:
            if vals.get('unit_price') is None:
                vals['gross_unit_price'] = Decimal(0)
                continue

            if 'gross_unit_price' not in vals:
                gross_unit_price = vals['unit_price']
                if vals.get('discount') not in (None, 1):
                    gross_unit_price = (gross_unit_price /
                        (1 - vals['discount']))
                if vals.get('contract'):
                    contract = Contract(vals['contract'])
                    contract_discount = contract.contract_discount
                    if contract_discount not in (None, 1):
                        gross_unit_price = (gross_unit_price /
                            (1 - contract_discount))
                if gross_unit_price != vals['unit_price']:
                    digits = cls.gross_unit_price.digits[1]
                    gross_unit_price = gross_unit_price.quantize(
                        Decimal(str(10.0 ** -digits)))
                vals['gross_unit_price'] = gross_unit_price
            if 'discount' not in vals:
                vals['discount'] = Decimal(0)
        return super(ContractLine, cls).create(vlist)


class ContractConsumption:
    'Contract Consumption'
    __name__ = 'contract.consumption'

    def get_invoice_line(self):
        line = super(ContractConsumption, self).get_invoice_line()
        if line:
            discount = None
            if self.contract_line.gross_unit_price != line.unit_price:
                line.gross_unit_price = round(line.unit_price, 4)
                line.discount = Decimal('0')
                if (self.contract_line.discount and self.contract and
                        self.contract.contract_discount):
                    discount = (Decimal('1.0') -
                        (Decimal('1.0') - self.contract_line.discount) *
                        (Decimal('1.0') - self.contract.contract_discount))
                    pass
                elif self.contract and self.contract.contract_discount:
                    discount = self.contract.contract_discount
                elif self.contract_line.discount:
                    discount = self.contract_line.discount

                if discount:
                    bonificacion = (discount * 100).to_eng_string().replace(
                        '.', ',') + '%'
                    line.description += ' BONIFICACIÓN %s' % bonificacion
            return line
