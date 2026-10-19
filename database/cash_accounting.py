"""Public, deterministic cash-ledger accounting. No strategy or trade-manager dependencies."""
from __future__ import annotations
from collections.abc import Iterable, Mapping
from decimal import Decimal, InvalidOperation

ALLOWED_KINDS = frozenset({'DEPOSIT','WITHDRAWAL','BUY','SELL','FEE','DIVIDEND'})


def money(value: object) -> Decimal:
    """Convert financial amounts exactly; reject nonfinite or sub-cent values."""
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError('Invalid monetary amount') from exc
    if not number.is_finite() or number != number.quantize(Decimal('0.01')):
        raise ValueError('Amount must be finite and in cents')
    return number


def reconcile_cash(opening_cash: object, events: Iterable[Mapping]) -> dict:
    """Replay cash flows ordered by (timestamp, event_id); enforce unique IDs.

    Event amount is a nonnegative cash magnitude. BUY/WITHDRAWAL/FEE debit;
    DEPOSIT/SELL/DIVIDEND credit. Realized P&L cannot be inferred from cash flows.
    """
    balance = money(opening_cash)
    if balance < 0:
        raise ValueError('Negative opening cash')
    normalized = []
    seen = set()
    for event in events:
        kind = str(event.get('kind','')).upper()
        if kind not in ALLOWED_KINDS:
            raise ValueError('Unsupported cash event kind')
        event_id = str(event.get('event_id','')).strip()
        when = str(event.get('timestamp','')).strip()
        if not event_id or not when or event_id in seen:
            raise ValueError('Missing or duplicate event ID or timestamp')
        seen.add(event_id)
        amount = money(event.get('amount'))
        if amount < 0:
            raise ValueError('Event magnitude must be nonnegative')
        normalized.append((when,event_id,kind,amount))
    for _, _, kind, amount in sorted(normalized):
        balance += amount if kind in {'DEPOSIT','SELL','DIVIDEND'} else -amount
        if balance < 0:
            raise ValueError('Cash ledger would become negative')
    return {'cash_balance': float(balance), 'event_count': len(normalized),
            'realized_pnl': None, 'reconciled': True}
