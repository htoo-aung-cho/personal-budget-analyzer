"""
Configuration for the Personal Budget Analyzer and Income‑Expense Tracker (version 3).

This module defines the lists of categories used for both income and
expense transactions.  Having them in a single location makes it
easy to modify or extend the category lists without digging through
the UI logic.  The mode constants are also defined here for
consistency with the database layer.
"""

# Categories used when logging income transactions.  These strings
# appear in the dropdown menu on the Add Income page of the
# application.  Feel free to adjust or extend these lists to suit
# your needs (for example, adding a "Gift" or "Rental" category).
INCOME_CATEGORIES = [
    "Salary",
    "Allowance",
    "Scholarship",
    "Freelance",
    "Other",
]

# Categories used when logging expense transactions.  These
# categories are deliberately broad to help keep the project
# approachable for a student assignment; you can always add more
# granular categories later.  They appear on the Add Expense page.
EXPENSE_CATEGORIES = [
    "Food",
    "Transport",
    "School",
    "Shopping",
    "Bills",
    "Entertainment",
    "Other",
]

# Constants used to identify the two tracking modes.  Storing these
# strings in one place helps avoid typos throughout the codebase.
MODE_MONTHLY_BUDGET = "monthly_budget"
MODE_BALANCE_TRACKING = "balance_tracking"