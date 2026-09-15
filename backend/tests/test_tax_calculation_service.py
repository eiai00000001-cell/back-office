from decimal import Decimal

import pytest

from app.enums import TaxCategory
from app.services.tax_calculation_service import TaxCalculationService


class TestCalculateItemAmount:
    def test_calculates_amount_as_quantity_times_unit_price(self):
        service = TaxCalculationService()
        assert service.calculate_item_amount(Decimal("2"), 1000) == 2000

    def test_floors_fractional_result(self):
        service = TaxCalculationService()
        # 1.33 * 100 = 133.0 -> no fraction here, use a case producing a fraction
        assert service.calculate_item_amount(Decimal("1.33"), 3) == 3  # floor(3.99) = 3

    def test_accepts_decimal_quantity_with_two_fraction_digits(self):
        service = TaxCalculationService()
        assert service.calculate_item_amount(Decimal("2.5"), 1000) == 2500


class TestAggregateByTaxCategory:
    def test_aggregates_amounts_grouped_by_tax_category(self):
        service = TaxCalculationService()
        items = [
            {"tax_category": TaxCategory.STANDARD_10, "amount": 300000},
            {"tax_category": TaxCategory.NON_TAXABLE, "amount": 5000},
            {"tax_category": TaxCategory.STANDARD_10, "amount": 10000},
        ]
        result = service.aggregate_by_tax_category(items)
        assert result[TaxCategory.STANDARD_10] == 310000
        assert result[TaxCategory.NON_TAXABLE] == 5000
        assert result.get(TaxCategory.OUT_OF_SCOPE, 0) == 0

    def test_returns_empty_aggregation_for_no_items(self):
        service = TaxCalculationService()
        assert service.aggregate_by_tax_category([]) == {}


class TestCalculateTaxAmount:
    def test_taxes_only_standard_10_category(self):
        service = TaxCalculationService()
        subtotal_by_tax = {
            TaxCategory.STANDARD_10: 300000,
            TaxCategory.NON_TAXABLE: 5000,
            TaxCategory.OUT_OF_SCOPE: 1000,
        }
        assert service.calculate_tax_amount(subtotal_by_tax) == 30000

    def test_floors_fractional_tax_amount(self):
        service = TaxCalculationService()
        subtotal_by_tax = {TaxCategory.STANDARD_10: 999}
        # 999 * 0.10 = 99.9 -> floor to 99
        assert service.calculate_tax_amount(subtotal_by_tax) == 99

    def test_returns_zero_when_no_standard_category(self):
        service = TaxCalculationService()
        subtotal_by_tax = {TaxCategory.NON_TAXABLE: 5000}
        assert service.calculate_tax_amount(subtotal_by_tax) == 0


class TestCalculateTotals:
    def test_calculates_full_totals_from_raw_items(self):
        service = TaxCalculationService()
        items = [
            {"quantity": Decimal("1"), "unit_price": 300000, "tax_category": TaxCategory.STANDARD_10},
            {"quantity": Decimal("1"), "unit_price": 0, "tax_category": TaxCategory.NON_TAXABLE},
        ]
        totals = service.calculate_totals(items)
        assert totals["item_amounts"] == [300000, 0]
        assert totals["subtotal_by_tax"][TaxCategory.STANDARD_10] == 300000
        assert totals["subtotal_amount"] == 300000
        assert totals["tax_amount"] == 30000
        assert totals["total_amount"] == 330000

    def test_totals_are_zero_for_empty_items(self):
        service = TaxCalculationService()
        totals = service.calculate_totals([])
        assert totals["item_amounts"] == []
        assert totals["subtotal_amount"] == 0
        assert totals["tax_amount"] == 0
        assert totals["total_amount"] == 0
