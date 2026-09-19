from enum import Enum, StrEnum


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


class ProjectStatus(StrEnum):
    """案件の進捗ステータス。カンバンの列順は宣言順(詳細設計書4.9.1章)。"""

    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_REVIEW = "WAITING_REVIEW"
    DONE = "DONE"


class DeadlineCategory(StrEnum):
    """手動登録の期限の種別(詳細設計書3.17章)。"""

    TAX_FILING = "TAX_FILING"
    CONTRACT_RENEWAL = "CONTRACT_RENEWAL"
    OTHER = "OTHER"


class NotificationSourceType(StrEnum):
    """通知の種類(詳細設計書4.10.1章)。宣言順は同日の並び順(TYPE_ORDER)を兼ねる。"""

    INVOICE_DUE = "INVOICE_DUE"
    QUOTE_EXPIRY = "QUOTE_EXPIRY"
    PROJECT_DUE = "PROJECT_DUE"
    DEADLINE = "DEADLINE"
