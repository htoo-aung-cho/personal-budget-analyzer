"""
Analysis routines for the Personal Budget Analyzer and Income‑Expense Tracker (version 3).

This module contains pure functions that compute summaries from
transaction records.  Isolating the analytical code makes it easy to
unit test the finance logic separately from the UI and database
layers.  In version 3 the analysis logic is unchanged from earlier
versions; the application now supports multiple independent
trackers but the summaries are still computed on per‑tracker
transaction lists.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Tuple, Dict


def calculate_summary(transactions: Iterable[Tuple[int, str, str, str, float, str]]) -> Dict[str, object]:
    """Compute high‑level summary statistics from a list of transactions.

    Parameters
    ----------
    transactions : iterable of tuple
        Each transaction tuple should have the form ``(id, date, type,
        category, amount, note)`` as returned by ``database.get_transactions``.

    Returns
    -------
    dict
        A dictionary containing total income, total expenses,
        remaining balance, category breakdowns and the names of the
        largest income and expense categories.
    """
    total_income = 0.0
    total_expense = 0.0
    income_by_category: defaultdict[str, float] = defaultdict(float)
    expense_by_category: defaultdict[str, float] = defaultdict(float)
    for _id, date_str, ttype, category, amount, note in transactions:
        if ttype == "income":
            total_income += amount
            income_by_category[category] += amount
        elif ttype == "expense":
            total_expense += amount
            expense_by_category[category] += amount
    balance = total_income - total_expense
    highest_income_category = None
    highest_expense_category = None
    if income_by_category:
        highest_income_category = max(income_by_category.items(), key=lambda x: x[1])[0]
    if expense_by_category:
        highest_expense_category = max(expense_by_category.items(), key=lambda x: x[1])[0]
    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "balance": balance,
        "income_by_category": dict(income_by_category),
        "expense_by_category": dict(expense_by_category),
        "highest_income_category": highest_income_category,
        "highest_expense_category": highest_expense_category,
    }


def calculate_monthly_expense(transactions: Iterable[Tuple[int, str, str, str, float, str]]) -> float:
    """Return the sum of expenses from the given list of transactions.

    This helper is useful for computing how much of a monthly budget
    has been spent.  Only transactions whose ``type`` is ``"expense"``
    contribute to the sum.

    Parameters
    ----------
    transactions : iterable of tuple
        Transactions as returned by ``database.get_transactions_for_month``.

    Returns
    -------
    float
        The total expense amount.
    """
    total = 0.0
    for _id, date_str, ttype, category, amount, note in transactions:
        if ttype == "expense":
            total += amount
    return total