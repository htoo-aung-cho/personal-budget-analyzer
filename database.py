"""
Database access layer for the Personal Budget Analyzer and Income‑Expense Tracker (version 3).

This module encapsulates all interactions with the SQLite database
used by the application.  In version 3 the schema has been
expanded to support multiple independent budget trackers.  Each
tracker has its own mode (monthly budget or balance tracking) and
associated starting parameters.  Transactions are linked to a
tracker via a ``tracker_id`` column.  A simple settings table
persists the ID of the currently active tracker.

The functions exposed here provide a high‑level API for
creating, reading, updating and deleting trackers and
transactions, as well as storing and retrieving global settings.
Separating the database logic from the UI code keeps
responsibilities clear and simplifies unit testing.
"""

from __future__ import annotations

import os
import sqlite3
from typing import Any, Iterable, Optional, Tuple, Dict

from datetime import datetime

# Determine the absolute path to the database file.  The database
# resides in the ``data`` subdirectory of this package.  If the
# directory does not exist it will be created by :func:`init_db`.
DB_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DB_DIR, "finance_data.db")


def init_db() -> None:
    """Initialise the SQLite database and upgrade the schema.

    This function ensures that the database file and required tables
    exist.  It creates a ``trackers`` table to store information
    about each budget tracker, a ``transactions`` table to store
    income and expense records for each tracker, and a ``settings``
    table to hold key/value configuration entries such as the
    currently active tracker ID.  If the directory for the database
    file does not exist it will be created.

    If upgrading from an earlier version of the schema, missing
    tables or columns will be added automatically.  Existing data
    will be preserved.
    """
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Create trackers table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS trackers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mode TEXT NOT NULL,
            monthly_budget REAL,
            start_balance REAL
        );
        """
    )
    # Create transactions table (if new install)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            type TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            note TEXT,
            tracker_id INTEGER
        );
        """
    )
    # Ensure tracker_id column exists in transactions.  Older
    # versions of the application did not have this column.  If it
    # doesn't exist we add it via an ALTER TABLE statement.  SQLite
    # does not support IF NOT EXISTS for ALTER TABLE, so we check
    # manually.
    cur.execute("PRAGMA table_info(transactions);")
    cols = [row[1] for row in cur.fetchall()]
    if "tracker_id" not in cols:
        cur.execute("ALTER TABLE transactions ADD COLUMN tracker_id INTEGER;")
    # Create settings table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """
    )
    conn.commit()
    conn.close()


# -------------------------------------------------------------------------
# Tracker management
def create_tracker(
    name: str,
    mode: str,
    monthly_budget: Optional[float] = None,
    start_balance: Optional[float] = None,
) -> int:
    """Create a new budget tracker.

    Parameters
    ----------
    name : str
        A human‑friendly name for the tracker (e.g. "Personal",
        "Restaurants").
    mode : str
        One of ``config.MODE_MONTHLY_BUDGET`` or
        ``config.MODE_BALANCE_TRACKING``.  No validation is
        performed here; invalid values will simply be stored.
    monthly_budget : float, optional
        The fixed monthly budget for the tracker (if applicable).
    start_balance : float, optional
        The starting balance for the tracker (if applicable).

    Returns
    -------
    int
        The ID of the newly created tracker.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO trackers (name, mode, monthly_budget, start_balance) VALUES (?, ?, ?, ?)",
        (name, mode, monthly_budget, start_balance),
    )
    tracker_id = cur.lastrowid
    conn.commit()
    conn.close()
    return tracker_id


def get_trackers() -> list[tuple[int, str, str, Optional[float], Optional[float]]]:
    """Return a list of all trackers.

    The trackers are returned sorted by their ID in ascending order.

    Returns
    -------
    list of tuple
        Each tuple contains ``(id, name, mode, monthly_budget, start_balance)``.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, mode, monthly_budget, start_balance FROM trackers ORDER BY id"
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_tracker(tracker_id: int) -> Optional[dict[str, Any]]:
    """Retrieve a tracker by its ID.

    Parameters
    ----------
    tracker_id : int
        The primary key of the tracker to fetch.

    Returns
    -------
    dict or None
        A dictionary with keys ``id``, ``name``, ``mode``, ``monthly_budget``
        and ``start_balance``, or ``None`` if the tracker does not exist.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, mode, monthly_budget, start_balance FROM trackers WHERE id = ?",
        (tracker_id,),
    )
    row = cur.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0],
            "name": row[1],
            "mode": row[2],
            "monthly_budget": row[3],
            "start_balance": row[4],
        }
    return None


def update_tracker(
    tracker_id: int,
    name: Optional[str] = None,
    mode: Optional[str] = None,
    monthly_budget: Optional[float] = None,
    start_balance: Optional[float] = None,
) -> None:
    """Update properties of an existing tracker.

    Any field passed as ``None`` will be left unchanged.  This allows
    callers to update only specific attributes.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Build dynamic update statement
    fields = []
    params: list[Any] = []
    if name is not None:
        fields.append("name = ?")
        params.append(name)
    if mode is not None:
        fields.append("mode = ?")
        params.append(mode)
    if monthly_budget is not None:
        fields.append("monthly_budget = ?")
        params.append(monthly_budget)
    if start_balance is not None:
        fields.append("start_balance = ?")
        params.append(start_balance)
    if not fields:
        conn.close()
        return
    params.append(tracker_id)
    query = f"UPDATE trackers SET {', '.join(fields)} WHERE id = ?"
    cur.execute(query, tuple(params))
    conn.commit()
    conn.close()


def delete_tracker(tracker_id: int) -> None:
    """Delete a tracker and all of its transactions.

    Parameters
    ----------
    tracker_id : int
        The ID of the tracker to delete.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Delete transactions first to maintain referential integrity
    cur.execute("DELETE FROM transactions WHERE tracker_id = ?", (tracker_id,))
    # Delete the tracker
    cur.execute("DELETE FROM trackers WHERE id = ?", (tracker_id,))
    # If the deleted tracker was active, remove it from settings
    cur.execute("DELETE FROM settings WHERE key = 'active_tracker_id' AND value = ?", (str(tracker_id),))
    conn.commit()
    conn.close()


def set_active_tracker_id(tracker_id: Optional[int]) -> None:
    """Set the currently active tracker.

    The active tracker ID is stored in the ``settings`` table under
    the key ``'active_tracker_id'``.  Passing ``None`` clears the
    active tracker selection.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    if tracker_id is None:
        cur.execute("DELETE FROM settings WHERE key = 'active_tracker_id'")
    else:
        cur.execute(
            "REPLACE INTO settings (key, value) VALUES ('active_tracker_id', ?)",
            (str(tracker_id),),
        )
    conn.commit()
    conn.close()


def get_active_tracker_id() -> Optional[int]:
    """Return the ID of the currently active tracker.

    Returns ``None`` if no active tracker has been set.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key = 'active_tracker_id'")
    row = cur.fetchone()
    conn.close()
    if row:
        try:
            return int(row[0])
        except ValueError:
            return None
    return None


def get_active_tracker() -> Optional[dict[str, Any]]:
    """Return the full tracker record for the active tracker, if any."""
    tracker_id = get_active_tracker_id()
    if tracker_id is None:
        return None
    return get_tracker(tracker_id)


# -------------------------------------------------------------------------
# Transaction management
def add_transaction(
    date: str,
    ttype: str,
    category: str,
    amount: float,
    note: str = "",
    tracker_id: Optional[int] = None,
) -> int:
    """Add an income or expense record to the database.

    Parameters
    ----------
    date : str
        The transaction date as an ISO formatted string (YYYY‑MM‑DD).
    ttype : str
        Either ``"income"`` or ``"expense"``.
    category : str
        The user‑selected category for this transaction.
    amount : float
        The monetary value of the transaction.  Income values should
        be positive.
    note : str, optional
        Optional free‑text note supplied by the user.
    tracker_id : int, optional
        The ID of the tracker this transaction belongs to.  If
        ``None`` is supplied the transaction will be associated with
        the currently active tracker.  If no active tracker is set
        an exception will be raised.

    Returns
    -------
    int
        The primary key of the newly created transaction.
    """
    if tracker_id is None:
        tracker_id = get_active_tracker_id()
    if tracker_id is None:
        raise RuntimeError("No active tracker selected")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO transactions (date, type, category, amount, note, tracker_id) VALUES (?, ?, ?, ?, ?, ?)",
        (date, ttype, category, amount, note, tracker_id),
    )
    tx_id = cur.lastrowid
    conn.commit()
    conn.close()
    return tx_id


def update_transaction(
    tx_id: int,
    date: Optional[str] = None,
    ttype: Optional[str] = None,
    category: Optional[str] = None,
    amount: Optional[float] = None,
    note: Optional[str] = None,
) -> None:
    """Update one or more fields of an existing transaction.

    Any field passed as ``None`` will be left unchanged.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    fields = []
    params: list[Any] = []
    if date is not None:
        fields.append("date = ?")
        params.append(date)
    if ttype is not None:
        fields.append("type = ?")
        params.append(ttype)
    if category is not None:
        fields.append("category = ?")
        params.append(category)
    if amount is not None:
        fields.append("amount = ?")
        params.append(amount)
    if note is not None:
        fields.append("note = ?")
        params.append(note)
    if not fields:
        conn.close()
        return
    params.append(tx_id)
    query = f"UPDATE transactions SET {', '.join(fields)} WHERE id = ?"
    cur.execute(query, tuple(params))
    conn.commit()
    conn.close()


def delete_transaction(tx_id: int) -> None:
    """Delete a transaction by its ID."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
    conn.commit()
    conn.close()


def get_transactions(tracker_id: Optional[int] = None) -> list[Tuple[int, str, str, str, float, str]]:
    """Return all transactions for the specified tracker.

    If ``tracker_id`` is ``None`` the currently active tracker will
    be used.  An exception is raised if there is no active tracker.

    Returns
    -------
    list of tuple
        Each tuple contains ``(id, date, type, category, amount, note)``.
    """
    if tracker_id is None:
        tracker_id = get_active_tracker_id()
    if tracker_id is None:
        raise RuntimeError("No active tracker selected")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, date, type, category, amount, note FROM transactions WHERE tracker_id = ? ORDER BY date DESC, id DESC",
        (tracker_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_transactions_for_month(
    year: int,
    month: int,
    tracker_id: Optional[int] = None,
) -> list[Tuple[int, str, str, str, float, str]]:
    """Return transactions for a specific month and tracker.

    Parameters
    ----------
    year : int
        The calendar year (e.g. 2026).
    month : int
        The calendar month (1‑12).
    tracker_id : int, optional
        The tracker whose transactions should be returned.  If
        ``None`` the current active tracker will be used.

    Returns
    -------
    list of tuple
        A list of transaction tuples ``(id, date, type, category, amount, note)``.
    """
    if tracker_id is None:
        tracker_id = get_active_tracker_id()
    if tracker_id is None:
        raise RuntimeError("No active tracker selected")
    start_date = f"{year:04d}-{month:02d}-01"
    if month == 12:
        end_year, end_month = year + 1, 1
    else:
        end_year, end_month = year, month + 1
    end_date = f"{end_year:04d}-{end_month:02d}-01"
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, date, type, category, amount, note FROM transactions WHERE tracker_id = ? AND date >= ? AND date < ? ORDER BY date DESC, id DESC",
        (tracker_id, start_date, end_date),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


# -------------------------------------------------------------------------
# Settings management
def set_setting(key: str, value: str) -> None:
    """Store a configuration value.

    If the key already exists, its value will be overwritten.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()


def get_setting(key: str) -> Optional[str]:
    """Retrieve a configuration value.

    Returns ``None`` if the key does not exist.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None