"""Tax calculation logic shared by F-01 (invoice) and F-03 (quote).

See 詳細設計書 4.1 ステップ1〜5.
"""
import math
from decimal import Decimal

from app.enums import TaxCategory

STANDARD_TAX_RATE = Decimal("0.10")


class TaxCalculationService:
    def calculate_item_amount(self, quantity: Decimal, unit_price: int) -> int:
        """amount = floor(quantity * unit_price)"""
        return math.floor(Decimal(quantity) * Decimal(unit_price))

    def aggregate_by_tax_category(self, items: list[dict]) -> dict[TaxCategory, int]:
        """Sum item amounts grouped by tax category."""
        result: dict[TaxCategory, int] = {}
        for item in items:
            category = item["tax_category"]
            result[category] = result.get(category, 0) + item["amount"]
        return result

    def calculate_tax_amount(self, subtotal_by_tax: dict[TaxCategory, int]) -> int:
        """Only the STANDARD_10 category is taxable; result is floored."""
        standard_subtotal = subtotal_by_tax.get(TaxCategory.STANDARD_10, 0)
        return math.floor(Decimal(standard_subtotal) * STANDARD_TAX_RATE)

    def calculate_totals(self, items: list[dict]) -> dict:
        """Full calculation pipeline (詳細設計書4.1 ステップ1〜5) for a list of
        raw item dicts with keys: quantity, unit_price, tax_category.
        """
        item_amounts = [
            self.calculate_item_amount(item["quantity"], item["unit_price"]) for item in items
        ]
        items_with_amount = [
            {"tax_category": item["tax_category"], "amount": amount}
            for item, amount in zip(items, item_amounts)
        ]
        subtotal_by_tax = self.aggregate_by_tax_category(items_with_amount)
        tax_amount = self.calculate_tax_amount(subtotal_by_tax)
        subtotal_amount = sum(subtotal_by_tax.values())
        total_amount = subtotal_amount + tax_amount
        return {
            "item_amounts": item_amounts,
            "subtotal_by_tax": subtotal_by_tax,
            "subtotal_amount": subtotal_amount,
            "tax_amount": tax_amount,
            "total_amount": total_amount,
        }
