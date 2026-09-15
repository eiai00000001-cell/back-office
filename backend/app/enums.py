from enum import Enum


class TaxCategory(str, Enum):
    """Tax category used for invoice/quote line items (3 categories)."""

    STANDARD_10 = "STANDARD_10"
    NON_TAXABLE = "NON_TAXABLE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class ExpenseTaxCategory(str, Enum):
    """Tax category used for expenses (4 categories, adds NOT_APPLICABLE)."""

    STANDARD_10 = "STANDARD_10"
    NON_TAXABLE = "NON_TAXABLE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class QuoteStatus(str, Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"


class PaymentStatus(str, Enum):
    UNPAID = "UNPAID"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"


class PaymentMethod(str, Enum):
    CASH = "CASH"
    CREDIT_CARD = "CREDIT_CARD"
    BANK_TRANSFER = "BANK_TRANSFER"
    OTHER = "OTHER"


ACCOUNT_CATEGORIES = [
    "旅費交通費",
    "通信費",
    "消耗品費",
    "水道光熱費",
    "地代家賃",
    "外注工賃",
    "接待交際費",
    "会議費",
    "新聞図書費",
    "支払手数料",
    "租税公課",
    "雑費",
    "その他",
]
