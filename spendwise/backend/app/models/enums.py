from enum import Enum


class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"


class PaymentMethod(str, Enum):
    CASH = "cash"
    UPI = "upi"
    DEBIT_CARD = "debit_card"
    CREDIT_CARD = "credit_card"
    NET_BANKING = "net_banking"
    BANK_TRANSFER = "bank_transfer"
    WALLET = "wallet"
    CHEQUE = "cheque"
    OTHER = "other"


TRANSACTION_TYPE_VALUES = tuple(t.value for t in TransactionType)
PAYMENT_METHOD_VALUES = tuple(p.value for p in PaymentMethod)
