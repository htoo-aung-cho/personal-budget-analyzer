"""
Main entry point and user interface for the Personal Budget Analyzer and
Income‑Expense Tracker (version 3).

This module brings together the database, analysis and configuration
components into a complete desktop application.  In version 3 the
application supports multiple independent budget trackers.  Users can
create, select and delete trackers, each of which maintains its own
transactions and settings.  Transactions can also be edited or
deleted after creation.  The modern, responsive user interface is
implemented using CustomTkinter.

To run the application execute this module directly with Python:

```
python3 main.py
```

The application stores its data in an SQLite database file located
under the ``data`` directory.  No external services are used, so
everything runs locally on your computer.
"""

from __future__ import annotations

import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime, date
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import database
import analyzer
import config


class App(ctk.CTk):
    """Main application class for version 3.

    This class manages the overall window, navigation and page
    switching logic.  It also holds state such as the currently
    active tracker and its associated budget or starting balance.
    """

    def __init__(self) -> None:
        super().__init__()
        # Initialise the database and upgrade the schema
        database.init_db()

        # Load the active tracker from settings (if any)
        self.active_tracker = database.get_active_tracker()
        # Mirror important tracker fields into instance attributes
        if self.active_tracker is not None:
            self.mode: str = self.active_tracker["mode"]
            self.monthly_budget: float | None = self.active_tracker["monthly_budget"]
            self.start_balance: float | None = self.active_tracker["start_balance"]
        else:
            self.mode = ""
            self.monthly_budget = None
            self.start_balance = None

        # Configure the application window
        self.title("Personal Budget Analyzer and Tracker")
        self.geometry("1000x650")
        self.minsize(900, 600)

        # Apply a light theme and a primary colour
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        # Use a 2‑column grid: a fixed‑width sidebar and a resizable content area
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar for navigation; created once a tracker is selected
        self.sidebar_frame: ctk.CTkFrame | None = None
        # Content container; holds the currently visible page
        self.content_frame: ctk.CTkFrame = ctk.CTkFrame(self, corner_radius=0)
        self.content_frame.grid(row=0, column=1, sticky="nsew")

        # Pages managed by the application
        self.pages: dict[str, ctk.CTkFrame] = {}

        # Initialise pages
        self.create_tracker_selection_page()
        self.create_mode_selection_page()
        self.create_dashboard_page()
        self.create_add_income_page()
        self.create_add_expense_page()
        self.create_analysis_page()
        self.create_settings_page()

        # If there is no active tracker, start at the tracker selection page
        if self.active_tracker is None:
            self.show_page("tracker_selection")
        else:
            # Create sidebar and show dashboard
            self.create_sidebar()
            self.show_page("dashboard")

    # ------------------------------------------------------------------
    # Page creation helpers
    def create_tracker_selection_page(self) -> None:
        """Set up the tracker management page.

        This page lists all existing trackers and provides buttons to
        create a new tracker or delete existing ones.  Selecting a
        tracker makes it active and transitions to the main
        application.
        """
        frame = ctk.CTkFrame(self.content_frame)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(2, weight=1)

        title_label = ctk.CTkLabel(
            frame,
            text="Select or Create a Tracker",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title_label.grid(row=0, column=0, pady=(30, 10))

        # Scrollable frame to list trackers
        self.trackers_scroll = ctk.CTkScrollableFrame(frame, height=350)
        self.trackers_scroll.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.trackers_scroll.grid_columnconfigure(0, weight=1)

        # Button to create a new tracker
        new_btn = ctk.CTkButton(
            frame,
            text="Create New Tracker",
            command=self.open_create_tracker_dialog,
            height=40,
        )
        new_btn.grid(row=2, column=0, pady=(10, 20))

        self.pages["tracker_selection"] = frame
        # Populate the list initially
        self.refresh_tracker_list()

    def refresh_tracker_list(self) -> None:
        """Refresh the list of trackers displayed on the tracker selection page."""
        # Clear existing entries
        for widget in self.trackers_scroll.winfo_children():
            widget.destroy()
        trackers = database.get_trackers()
        if not trackers:
            empty_label = ctk.CTkLabel(
                self.trackers_scroll,
                text="No trackers available. Click the button below to create one.",
                wraplength=600,
            )
            empty_label.grid(row=0, column=0, padx=10, pady=10)
            return
        row = 0
        for tid, name, mode, monthly_budget, start_balance in trackers:
            # Frame for each tracker row
            row_frame = ctk.CTkFrame(self.trackers_scroll)
            row_frame.grid(row=row, column=0, padx=5, pady=5, sticky="ew")
            for col, weight in enumerate((3, 1, 1)):
                row_frame.grid_columnconfigure(col, weight=weight)
            # Tracker info label
            info_text = f"{name}  (Mode: {'Monthly' if mode == config.MODE_MONTHLY_BUDGET else 'Balance'})"
            info_lbl = ctk.CTkLabel(row_frame, text=info_text, anchor="w")
            info_lbl.grid(row=0, column=0, padx=5, sticky="w")
            # Open button
            open_btn = ctk.CTkButton(
                row_frame,
                text="Open",
                width=60,
                command=lambda t_id=tid: self.activate_tracker(t_id),
            )
            open_btn.grid(row=0, column=1, padx=5)
            # Delete button
            del_btn = ctk.CTkButton(
                row_frame,
                text="Delete",
                width=60,
                fg_color="red",
                hover_color="#cc0000",
                command=lambda t_id=tid: self.confirm_delete_tracker(t_id),
            )
            del_btn.grid(row=0, column=2, padx=5)
            row += 1

    def confirm_delete_tracker(self, tracker_id: int) -> None:
        """Prompt the user to confirm deletion of a tracker."""
        if messagebox.askyesno(
            "Delete Tracker",
            "Are you sure you want to delete this tracker? All data for this tracker will be lost.",
        ):
            database.delete_tracker(tracker_id)
            # If the deleted tracker was active, clear active tracker
            if self.active_tracker and self.active_tracker["id"] == tracker_id:
                self.active_tracker = None
                self.mode = ""
                self.monthly_budget = None
                self.start_balance = None
            self.refresh_tracker_list()

    def activate_tracker(self, tracker_id: int) -> None:
        """Make the given tracker the active tracker and transition to the main app."""
        database.set_active_tracker_id(tracker_id)
        self.active_tracker = database.get_tracker(tracker_id)
        if self.active_tracker:
            self.mode = self.active_tracker["mode"]
            self.monthly_budget = self.active_tracker["monthly_budget"]
            self.start_balance = self.active_tracker["start_balance"]
        # Create sidebar if not yet created
        self.create_sidebar()
        # Refresh dashboard
        self.refresh_dashboard()
        self.show_page("dashboard")

    def open_create_tracker_dialog(self) -> None:
        """Open a modal dialog to create a new tracker."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Create New Tracker")
        dialog.geometry("400x300")
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(dialog, text="Tracker Name:").grid(row=0, column=0, padx=10, pady=10, sticky="e")
        name_var = ctk.StringVar()
        name_entry = ctk.CTkEntry(dialog, textvariable=name_var)
        name_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(dialog, text="Mode:").grid(row=1, column=0, padx=10, pady=10, sticky="e")
        mode_var = ctk.StringVar(value=config.MODE_MONTHLY_BUDGET)
        mode_menu = ctk.CTkOptionMenu(dialog, values=["monthly_budget", "balance_tracking"], variable=mode_var)
        mode_menu.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(dialog, text="Monthly Budget (optional):").grid(row=2, column=0, padx=10, pady=10, sticky="e")
        budget_var = ctk.StringVar()
        budget_entry = ctk.CTkEntry(dialog, textvariable=budget_var)
        budget_entry.grid(row=2, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(dialog, text="Start Balance (optional):").grid(row=3, column=0, padx=10, pady=10, sticky="e")
        balance_var = ctk.StringVar()
        balance_entry = ctk.CTkEntry(dialog, textvariable=balance_var)
        balance_entry.grid(row=3, column=1, padx=10, pady=10, sticky="ew")

        def create_and_close() -> None:
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("Invalid Name", "Please enter a tracker name.")
                return
            mode_choice = mode_var.get()
            # Parse optional numeric fields
            mbudget = None
            sbalance = None
            if budget_var.get().strip():
                try:
                    mbudget = float(budget_var.get())
                except ValueError:
                    messagebox.showerror("Invalid Budget", "Monthly budget must be a number.")
                    return
            if balance_var.get().strip():
                try:
                    sbalance = float(balance_var.get())
                except ValueError:
                    messagebox.showerror("Invalid Balance", "Start balance must be a number.")
                    return
            # Create tracker in DB
            t_id = database.create_tracker(name, mode_choice, mbudget, sbalance)
            # Set as active tracker
            database.set_active_tracker_id(t_id)
            self.active_tracker = database.get_tracker(t_id)
            self.mode = self.active_tracker["mode"]
            self.monthly_budget = self.active_tracker["monthly_budget"]
            self.start_balance = self.active_tracker["start_balance"]
            # Refresh tracker list and switch to dashboard
            self.refresh_tracker_list()
            self.create_sidebar()
            self.refresh_dashboard()
            self.show_page("dashboard")
            dialog.destroy()

        ctk.CTkButton(dialog, text="Create", command=create_and_close).grid(row=4, column=0, columnspan=2, pady=20)

    # Mode selection page (per tracker) reused for editing tracker mode
    def create_mode_selection_page(self) -> None:
        """Set up the mode selection page used when first creating a tracker.

        This page is retained for backwards compatibility but is no longer
        shown at application startup.  It can be used when editing an
        existing tracker to change its mode and parameters.
        """
        frame = ctk.CTkFrame(self.content_frame)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        title_label = ctk.CTkLabel(
            frame,
            text="Choose Tracking Mode",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title_label.grid(row=0, column=0, pady=(40, 20), padx=20)

        monthly_button = ctk.CTkButton(
            frame,
            text="Monthly Budget Mode",
            command=lambda: self._set_tracker_mode(config.MODE_MONTHLY_BUDGET),
            height=50,
            width=250,
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        monthly_button.grid(row=1, column=0, pady=(10, 10), padx=20)

        balance_button = ctk.CTkButton(
            frame,
            text="Balance Tracking Mode",
            command=lambda: self._set_tracker_mode(config.MODE_BALANCE_TRACKING),
            height=50,
            width=250,
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        balance_button.grid(row=2, column=0, pady=(10, 10), padx=20)

        self.pages["mode_selection"] = frame

    def _set_tracker_mode(self, mode: str) -> None:
        """Helper to set the mode of the active tracker (used in settings)."""
        if not self.active_tracker:
            return
        database.update_tracker(self.active_tracker["id"], mode=mode)
        self.active_tracker = database.get_tracker(self.active_tracker["id"])
        self.mode = self.active_tracker["mode"]
        messagebox.showinfo("Tracker Updated", "Tracking mode updated. Please adjust your budget/start balance if needed.")
        # Show settings page again
        self.refresh_dashboard()
        self.show_page("settings")

    def create_sidebar(self) -> None:
        """Create the persistent sidebar once a tracker has been selected."""
        if self.sidebar_frame is not None:
            return
        self.sidebar_frame = ctk.CTkFrame(self, corner_radius=0, width=180)
        self.sidebar_frame.grid(row=0, column=0, sticky="ns")
        # Layout rows; allow extra space below
        self.sidebar_frame.grid_rowconfigure((0, 1, 2, 3, 4, 5, 6), weight=1)
        self.sidebar_frame.grid_rowconfigure(7, weight=5)

        header = ctk.CTkLabel(
            self.sidebar_frame,
            text="Budget Tracker",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        header.grid(row=0, column=0, pady=(20, 10), padx=10)

        btn_dashboard = ctk.CTkButton(
            self.sidebar_frame,
            text="Dashboard",
            command=lambda: self.show_page("dashboard"),
        )
        btn_dashboard.grid(row=1, column=0, pady=5, padx=10, sticky="ew")

        btn_income = ctk.CTkButton(
            self.sidebar_frame,
            text="Add Income",
            command=lambda: self.show_page("add_income"),
        )
        btn_income.grid(row=2, column=0, pady=5, padx=10, sticky="ew")

        btn_expense = ctk.CTkButton(
            self.sidebar_frame,
            text="Add Expense",
            command=lambda: self.show_page("add_expense"),
        )
        btn_expense.grid(row=3, column=0, pady=5, padx=10, sticky="ew")

        btn_analysis = ctk.CTkButton(
            self.sidebar_frame,
            text="Analysis",
            command=lambda: self.show_page("analysis"),
        )
        btn_analysis.grid(row=4, column=0, pady=5, padx=10, sticky="ew")

        btn_settings = ctk.CTkButton(
            self.sidebar_frame,
            text="Settings",
            command=lambda: self.show_page("settings"),
        )
        btn_settings.grid(row=5, column=0, pady=5, padx=10, sticky="ew")

        btn_manage = ctk.CTkButton(
            self.sidebar_frame,
            text="Manage Trackers",
            command=lambda: self.show_page("tracker_selection"),
        )
        btn_manage.grid(row=6, column=0, pady=5, padx=10, sticky="ew")

        # Spacer row (empty frame) to fill remaining space
        spacer = ctk.CTkFrame(self.sidebar_frame)
        spacer.grid(row=7, column=0, sticky="ns")

    def create_dashboard_page(self) -> None:
        """Construct the dashboard page.

        The dashboard displays high‑level financial statistics
        (total income, total expenses, remaining balance and budget
        usage) as well as a list of recent transactions.  It updates
        dynamically whenever a new transaction is added or when the
        underlying data changes.
        """
        frame = ctk.CTkFrame(self.content_frame)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(5, weight=1)

        title = ctk.CTkLabel(frame, text="Dashboard", font=ctk.CTkFont(size=24, weight="bold"))
        title.grid(row=0, column=0, pady=(20, 10))

        # Top summary cards: income, expenses, balance, budget usage
        summary_frame = ctk.CTkFrame(frame)
        summary_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        summary_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.income_var = ctk.StringVar()
        self.expense_var = ctk.StringVar()
        self.balance_var = ctk.StringVar()
        self.budget_usage_var = ctk.StringVar()

        income_card = self._create_summary_card(summary_frame, "Total Income", self.income_var)
        income_card.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        expense_card = self._create_summary_card(summary_frame, "Total Expenses", self.expense_var)
        expense_card.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        balance_card = self._create_summary_card(summary_frame, "Balance", self.balance_var)
        balance_card.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")
        budget_card = self._create_summary_card(summary_frame, "Budget Used", self.budget_usage_var)
        budget_card.grid(row=0, column=3, padx=5, pady=5, sticky="nsew")

        # Progress bar for budget usage; only visible in monthly budget mode
        self.budget_progress = ctk.CTkProgressBar(summary_frame)
        self.budget_progress.grid(row=1, column=3, padx=5, pady=(0, 5), sticky="ew")

        # Recent transactions label
        recent_label = ctk.CTkLabel(
            frame,
            text="Recent Transactions",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        recent_label.grid(row=2, column=0, pady=(20, 5), padx=20, sticky="w")

        # Scrollable frame to list transactions
        self.transactions_scroll = ctk.CTkScrollableFrame(frame, height=300)
        self.transactions_scroll.grid(row=3, column=0, padx=20, pady=10, sticky="nsew")
        self.transactions_scroll.grid_columnconfigure(0, weight=1)

        # Table header row with extra Edit/Delete columns
        header_frame = ctk.CTkFrame(self.transactions_scroll)
        header_frame.grid(row=0, column=0, sticky="ew")
        for col, weight in enumerate((1, 1, 1, 1, 0, 0)):
            header_frame.grid_columnconfigure(col, weight=weight)
        ctk.CTkLabel(header_frame, text="Date", anchor="w", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, sticky="w", padx=5)
        ctk.CTkLabel(header_frame, text="Type", anchor="w", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=1, sticky="w", padx=5)
        ctk.CTkLabel(header_frame, text="Category", anchor="w", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=2, sticky="w", padx=5)
        ctk.CTkLabel(header_frame, text="Amount", anchor="e", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=3, sticky="e", padx=5)
        ctk.CTkLabel(header_frame, text="Edit", anchor="center", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=4, padx=5)
        ctk.CTkLabel(header_frame, text="Del", anchor="center", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=5, padx=5)

        self.transactions_list_start_row = 1  # first row for data

        self.pages["dashboard"] = frame

    def _create_summary_card(self, parent: ctk.CTkFrame, title: str, text_var: ctk.StringVar) -> ctk.CTkFrame:
        """Helper to create a summary statistics card."""
        card = ctk.CTkFrame(parent, border_width=1, border_color="gray75", corner_radius=8)
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=14)).grid(row=0, column=0, pady=(10, 0), padx=10, sticky="w")
        value_label = ctk.CTkLabel(card, textvariable=text_var, font=ctk.CTkFont(size=20, weight="bold"))
        value_label.grid(row=1, column=0, pady=(5, 10), padx=10, sticky="w")
        return card

    def create_add_income_page(self) -> None:
        """Set up the Add Income page."""
        frame = ctk.CTkFrame(self.content_frame)
        frame.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(frame, text="Add Income", font=ctk.CTkFont(size=24, weight="bold"))
        title.grid(row=0, column=0, pady=(20, 10))

        form = ctk.CTkFrame(frame)
        form.grid(row=1, column=0, padx=20, pady=10, sticky="nw")
        form.grid_columnconfigure((1), weight=1)

        # Category dropdown
        ctk.CTkLabel(form, text="Category:").grid(row=0, column=0, pady=5, padx=5, sticky="w")
        self.income_category_var = ctk.StringVar(value=config.INCOME_CATEGORIES[0])
        category_menu = ctk.CTkOptionMenu(form, values=config.INCOME_CATEGORIES, variable=self.income_category_var)
        category_menu.grid(row=0, column=1, pady=5, padx=5, sticky="ew")

        # Amount entry
        ctk.CTkLabel(form, text="Amount:").grid(row=1, column=0, pady=5, padx=5, sticky="w")
        self.income_amount_var = ctk.StringVar()
        amount_entry = ctk.CTkEntry(form, textvariable=self.income_amount_var)
        amount_entry.grid(row=1, column=1, pady=5, padx=5, sticky="ew")

        # Date entry (default to today)
        ctk.CTkLabel(form, text="Date (YYYY-MM-DD):").grid(row=2, column=0, pady=5, padx=5, sticky="w")
        self.income_date_var = ctk.StringVar(value=date.today().isoformat())
        date_entry = ctk.CTkEntry(form, textvariable=self.income_date_var)
        date_entry.grid(row=2, column=1, pady=5, padx=5, sticky="ew")

        # Note entry
        ctk.CTkLabel(form, text="Note:").grid(row=3, column=0, pady=5, padx=5, sticky="w")
        self.income_note_var = ctk.StringVar()
        note_entry = ctk.CTkEntry(form, textvariable=self.income_note_var)
        note_entry.grid(row=3, column=1, pady=5, padx=5, sticky="ew")

        # Submit button
        submit_btn = ctk.CTkButton(form, text="Add Income", command=self.submit_income)
        submit_btn.grid(row=4, column=0, columnspan=2, pady=15)

        self.pages["add_income"] = frame

    def submit_income(self) -> None:
        """Handle the Add Income form submission."""
        if not self.active_tracker:
            messagebox.showerror("No Tracker", "Please select or create a tracker first.")
            return
        category = self.income_category_var.get()
        amount_str = self.income_amount_var.get()
        date_str = self.income_date_var.get()
        note = self.income_note_var.get()
        # Basic validation
        try:
            amount = float(amount_str)
        except ValueError:
            messagebox.showerror("Invalid Amount", "Please enter a valid number for the amount.")
            return
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Invalid Date", "Please enter the date in YYYY-MM-DD format.")
            return
        database.add_transaction(date_str, "income", category, amount, note, tracker_id=self.active_tracker["id"])
        messagebox.showinfo("Income Added", "Income transaction has been recorded.")
        # Clear form
        self.income_amount_var.set("")
        self.income_note_var.set("")
        # Refresh dashboard
        self.refresh_dashboard()
        # Return to dashboard
        self.show_page("dashboard")

    def create_add_expense_page(self) -> None:
        """Set up the Add Expense page."""
        frame = ctk.CTkFrame(self.content_frame)
        frame.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(frame, text="Add Expense", font=ctk.CTkFont(size=24, weight="bold"))
        title.grid(row=0, column=0, pady=(20, 10))

        form = ctk.CTkFrame(frame)
        form.grid(row=1, column=0, padx=20, pady=10, sticky="nw")
        form.grid_columnconfigure((1), weight=1)

        # Category dropdown
        ctk.CTkLabel(form, text="Category:").grid(row=0, column=0, pady=5, padx=5, sticky="w")
        self.expense_category_var = ctk.StringVar(value=config.EXPENSE_CATEGORIES[0])
        category_menu = ctk.CTkOptionMenu(form, values=config.EXPENSE_CATEGORIES, variable=self.expense_category_var)
        category_menu.grid(row=0, column=1, pady=5, padx=5, sticky="ew")

        # Amount entry
        ctk.CTkLabel(form, text="Amount:").grid(row=1, column=0, pady=5, padx=5, sticky="w")
        self.expense_amount_var = ctk.StringVar()
        amount_entry = ctk.CTkEntry(form, textvariable=self.expense_amount_var)
        amount_entry.grid(row=1, column=1, pady=5, padx=5, sticky="ew")

        # Date entry
        ctk.CTkLabel(form, text="Date (YYYY-MM-DD):").grid(row=2, column=0, pady=5, padx=5, sticky="w")
        self.expense_date_var = ctk.StringVar(value=date.today().isoformat())
        date_entry = ctk.CTkEntry(form, textvariable=self.expense_date_var)
        date_entry.grid(row=2, column=1, pady=5, padx=5, sticky="ew")

        # Note entry
        ctk.CTkLabel(form, text="Note:").grid(row=3, column=0, pady=5, padx=5, sticky="w")
        self.expense_note_var = ctk.StringVar()
        note_entry = ctk.CTkEntry(form, textvariable=self.expense_note_var)
        note_entry.grid(row=3, column=1, pady=5, padx=5, sticky="ew")

        submit_btn = ctk.CTkButton(form, text="Add Expense", command=self.submit_expense)
        submit_btn.grid(row=4, column=0, columnspan=2, pady=15)

        self.pages["add_expense"] = frame

    def submit_expense(self) -> None:
        """Handle the Add Expense form submission."""
        if not self.active_tracker:
            messagebox.showerror("No Tracker", "Please select or create a tracker first.")
            return
        category = self.expense_category_var.get()
        amount_str = self.expense_amount_var.get()
        date_str = self.expense_date_var.get()
        note = self.expense_note_var.get()
        try:
            amount = float(amount_str)
        except ValueError:
            messagebox.showerror("Invalid Amount", "Please enter a valid number for the amount.")
            return
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Invalid Date", "Please enter the date in YYYY-MM-DD format.")
            return
        database.add_transaction(date_str, "expense", category, amount, note, tracker_id=self.active_tracker["id"])
        messagebox.showinfo("Expense Added", "Expense transaction has been recorded.")
        self.expense_amount_var.set("")
        self.expense_note_var.set("")
        self.refresh_dashboard()
        self.show_page("dashboard")

    def create_analysis_page(self) -> None:
        """Construct the analysis page."""
        frame = ctk.CTkFrame(self.content_frame)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(3, weight=1)

        title = ctk.CTkLabel(frame, text="Analysis", font=ctk.CTkFont(size=24, weight="bold"))
        title.grid(row=0, column=0, pady=(20, 10))

        # Summary labels
        self.analysis_income_var = ctk.StringVar()
        self.analysis_expense_var = ctk.StringVar()
        self.analysis_balance_var = ctk.StringVar()
        self.analysis_top_income_category_var = ctk.StringVar()
        self.analysis_top_expense_category_var = ctk.StringVar()

        info_frame = ctk.CTkFrame(frame)
        info_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        info_frame.grid_columnconfigure((0, 1), weight=1)

        # Total income/expense/balance labels
        ctk.CTkLabel(info_frame, text="Total Income:").grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(info_frame, textvariable=self.analysis_income_var).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(info_frame, text="Total Expenses:").grid(row=1, column=0, sticky="w")
        ctk.CTkLabel(info_frame, textvariable=self.analysis_expense_var).grid(row=1, column=1, sticky="w")
        ctk.CTkLabel(info_frame, text="Balance:").grid(row=2, column=0, sticky="w")
        ctk.CTkLabel(info_frame, textvariable=self.analysis_balance_var).grid(row=2, column=1, sticky="w")
        ctk.CTkLabel(info_frame, text="Top Income Category:").grid(row=3, column=0, sticky="w")
        ctk.CTkLabel(info_frame, textvariable=self.analysis_top_income_category_var).grid(row=3, column=1, sticky="w")
        ctk.CTkLabel(info_frame, text="Top Expense Category:").grid(row=4, column=0, sticky="w")
        ctk.CTkLabel(info_frame, textvariable=self.analysis_top_expense_category_var).grid(row=4, column=1, sticky="w")

        # Chart canvas area for category breakdown
        self.analysis_canvas_frame = ctk.CTkFrame(frame)
        self.analysis_canvas_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.analysis_canvas_frame.grid_columnconfigure(0, weight=1)
        self.analysis_canvas_frame.grid_rowconfigure(0, weight=1)

        self.pages["analysis"] = frame

    def refresh_analysis(self) -> None:
        """Refresh the data displayed on the analysis page."""
        if not self.active_tracker:
            return
        txns = database.get_transactions(self.active_tracker["id"])
        summary = analyzer.calculate_summary(txns)
        self.analysis_income_var.set(f"{summary['total_income']:.2f}")
        self.analysis_expense_var.set(f"{summary['total_expense']:.2f}")
        self.analysis_balance_var.set(f"{summary['balance']:.2f}")
        hi = summary["highest_income_category"] or "None"
        he = summary["highest_expense_category"] or "None"
        self.analysis_top_income_category_var.set(hi)
        self.analysis_top_expense_category_var.set(he)
        # Clear previous chart
        for widget in self.analysis_canvas_frame.winfo_children():
            widget.destroy()
        # Draw expense breakdown bar chart if there are expenses
        if summary["expense_by_category"]:
            categories = list(summary["expense_by_category"].keys())
            amounts = list(summary["expense_by_category"].values())
            fig, ax = plt.subplots(figsize=(4, 3))
            ax.bar(categories, amounts)
            ax.set_xlabel("Expense Categories")
            ax.set_ylabel("Amount")
            ax.set_title("Expenses by Category")
            fig.tight_layout()
            canvas = FigureCanvasTkAgg(fig, master=self.analysis_canvas_frame)
            canvas.draw()
            canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        else:
            msg = ctk.CTkLabel(self.analysis_canvas_frame, text="No expenses to analyse yet.")
            msg.grid(row=0, column=0)

    def create_settings_page(self) -> None:
        """Construct the settings page.

        The settings page allows the user to view and edit properties of
        the current tracker and reset parameters.  It also offers a
        button to return to the tracker selection screen.
        """
        frame = ctk.CTkFrame(self.content_frame)
        frame.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(frame, text="Settings", font=ctk.CTkFont(size=24, weight="bold"))
        title.grid(row=0, column=0, pady=(20, 10))

        # Current tracker info
        self.settings_tracker_name_var = ctk.StringVar()
        self.settings_mode_var = ctk.StringVar()
        self.settings_monthly_budget_var = ctk.StringVar()
        self.settings_start_balance_var = ctk.StringVar()

        info_frame = ctk.CTkFrame(frame)
        info_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        info_frame.grid_columnconfigure((0, 1), weight=1)

        # Labels and entries
        ctk.CTkLabel(info_frame, text="Tracker Name:").grid(row=0, column=0, sticky="w")
        name_entry = ctk.CTkEntry(info_frame, textvariable=self.settings_tracker_name_var)
        name_entry.grid(row=0, column=1, sticky="ew")
        ctk.CTkLabel(info_frame, text="Mode:").grid(row=1, column=0, sticky="w")
        mode_option = ctk.CTkOptionMenu(info_frame, values=["monthly_budget", "balance_tracking"], variable=self.settings_mode_var)
        mode_option.grid(row=1, column=1, sticky="ew")
        ctk.CTkLabel(info_frame, text="Monthly Budget:").grid(row=2, column=0, sticky="w")
        mb_entry = ctk.CTkEntry(info_frame, textvariable=self.settings_monthly_budget_var)
        mb_entry.grid(row=2, column=1, sticky="ew")
        ctk.CTkLabel(info_frame, text="Start Balance:").grid(row=3, column=0, sticky="w")
        sb_entry = ctk.CTkEntry(info_frame, textvariable=self.settings_start_balance_var)
        sb_entry.grid(row=3, column=1, sticky="ew")

        def save_tracker_settings() -> None:
            if not self.active_tracker:
                return
            name = self.settings_tracker_name_var.get().strip() or self.active_tracker["name"]
            mode = self.settings_mode_var.get()
            # Parse budgets
            mbudget = None
            sbalance = None
            if self.settings_monthly_budget_var.get().strip():
                try:
                    mbudget = float(self.settings_monthly_budget_var.get())
                except ValueError:
                    messagebox.showerror("Invalid Budget", "Monthly budget must be numeric.")
                    return
            if self.settings_start_balance_var.get().strip():
                try:
                    sbalance = float(self.settings_start_balance_var.get())
                except ValueError:
                    messagebox.showerror("Invalid Balance", "Start balance must be numeric.")
                    return
            database.update_tracker(self.active_tracker["id"], name=name, mode=mode, monthly_budget=mbudget, start_balance=sbalance)
            # Reload active tracker
            self.active_tracker = database.get_tracker(self.active_tracker["id"])
            self.mode = self.active_tracker["mode"]
            self.monthly_budget = self.active_tracker["monthly_budget"]
            self.start_balance = self.active_tracker["start_balance"]
            messagebox.showinfo("Saved", "Tracker settings saved.")
            self.refresh_dashboard()
        save_btn = ctk.CTkButton(info_frame, text="Save", command=save_tracker_settings)
        save_btn.grid(row=4, column=0, columnspan=2, pady=10)

        # Button to go back to tracker selection
        back_btn = ctk.CTkButton(frame, text="Back to Trackers", command=lambda: self.show_page("tracker_selection"))
        back_btn.grid(row=2, column=0, pady=20)

        self.pages["settings"] = frame

    # ------------------------------------------------------------------
    # Page switching
    def show_page(self, name: str) -> None:
        """Show the selected page and hide the others."""
        for page in self.pages.values():
            page.grid_forget()

        page = self.pages[name]
        page.grid(row=0, column=0, sticky="nsew")

        if name == "dashboard":
            self.refresh_dashboard()
        elif name == "analysis":
            self.refresh_analysis()
        elif name == "settings":
            self.refresh_settings()
        elif name == "tracker_selection":
            self.refresh_tracker_list()

    def refresh_settings(self) -> None:
        """Populate the settings page with current tracker details."""
        if not self.active_tracker:
            # Clear fields
            self.settings_tracker_name_var.set("")
            self.settings_mode_var.set("")
            self.settings_monthly_budget_var.set("")
            self.settings_start_balance_var.set("")
            return
        self.settings_tracker_name_var.set(self.active_tracker["name"])
        self.settings_mode_var.set(self.active_tracker["mode"])
        # For None values display empty string
        self.settings_monthly_budget_var.set("" if self.active_tracker["monthly_budget"] is None else str(self.active_tracker["monthly_budget"]))
        self.settings_start_balance_var.set("" if self.active_tracker["start_balance"] is None else str(self.active_tracker["start_balance"]))

    def refresh_dashboard(self) -> None:
        """Recalculate summary statistics and repopulate the transaction list."""
        if not self.active_tracker:
            # Clear summaries and list if no tracker
            self.income_var.set("0.00")
            self.expense_var.set("0.00")
            self.balance_var.set("0.00")
            self.budget_usage_var.set("0%")
            self.budget_progress.set(0.0)
            for child in self.transactions_scroll.winfo_children():
                if child != self.transactions_scroll.winfo_children()[0]:
                    child.destroy()
            return
        # Fetch transactions and compute summary
        txns = database.get_transactions(self.active_tracker["id"])
        summary = analyzer.calculate_summary(txns)
        total_income = summary["total_income"]
        total_expense = summary["total_expense"]
        balance = summary["balance"]
        # Balance tracking mode uses starting balance
        if self.mode == config.MODE_BALANCE_TRACKING:
            if self.start_balance is not None:
                balance = self.start_balance + total_income - total_expense
        self.income_var.set(f"{total_income:.2f}")
        self.expense_var.set(f"{total_expense:.2f}")
        self.balance_var.set(f"{balance:.2f}")
        # Compute budget usage if monthly budget mode
        if self.mode == config.MODE_MONTHLY_BUDGET and self.monthly_budget:
            # Sum of expenses for current month only
            today = date.today()
            month_txns = database.get_transactions_for_month(today.year, today.month, tracker_id=self.active_tracker["id"])
            month_expense = analyzer.calculate_monthly_expense(month_txns)
            usage_ratio = month_expense / self.monthly_budget if self.monthly_budget > 0 else 0.0
            usage_percent = min(usage_ratio * 100.0, 100.0)
            self.budget_usage_var.set(f"{usage_percent:.1f}%")
            self.budget_progress.set(min(usage_ratio, 1.0))
        else:
            self.budget_usage_var.set("—")
            self.budget_progress.set(0.0)
        # Populate transaction list
        # Remove existing transaction rows except header
        for child in self.transactions_scroll.winfo_children()[1:]:
            child.destroy()
        row = self.transactions_list_start_row
        for tx_id, tx_date, tx_type, tx_cat, tx_amount, tx_note in txns:
            row_frame = ctk.CTkFrame(self.transactions_scroll)
            row_frame.grid(row=row, column=0, sticky="ew")
            for col, weight in enumerate((1, 1, 1, 1, 0, 0)):
                row_frame.grid_columnconfigure(col, weight=weight)
            # Data labels
            ctk.CTkLabel(row_frame, text=tx_date, anchor="w").grid(row=0, column=0, sticky="w", padx=5)
            ctk.CTkLabel(row_frame, text="Income" if tx_type == "income" else "Expense", anchor="w").grid(row=0, column=1, sticky="w", padx=5)
            ctk.CTkLabel(row_frame, text=tx_cat, anchor="w").grid(row=0, column=2, sticky="w", padx=5)
            ctk.CTkLabel(row_frame, text=f"{tx_amount:.2f}", anchor="e").grid(row=0, column=3, sticky="e", padx=5)
            # Edit button
            edit_btn = ctk.CTkButton(
                row_frame,
                text="Edit",
                width=40,
                height=24,
                command=lambda tid=tx_id: self.open_edit_transaction_dialog(tid),
            )
            edit_btn.grid(row=0, column=4, padx=2, pady=2)
            # Delete button
            del_btn = ctk.CTkButton(
                row_frame,
                text="Del",
                width=40,
                height=24,
                fg_color="red",
                hover_color="#cc0000",
                command=lambda tid=tx_id: self.confirm_delete_transaction(tid),
            )
            del_btn.grid(row=0, column=5, padx=2, pady=2)
            row += 1

    def open_edit_transaction_dialog(self, tx_id: int) -> None:
        """Open a modal dialog to edit an existing transaction."""
        # Fetch current transaction details
        txns = database.get_transactions(self.active_tracker["id"])
        tx_data = None
        for t in txns:
            if t[0] == tx_id:
                tx_data = t
                break
        if tx_data is None:
            return
        # tx_data: (id, date, type, category, amount, note)
        dialog = ctk.CTkToplevel(self)
        dialog.title("Edit Transaction")
        dialog.geometry("400x300")
        dialog.grab_set()
        dialog.grid_columnconfigure((1), weight=1)
        ctk.CTkLabel(dialog, text="Date (YYYY-MM-DD):").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        date_var = ctk.StringVar(value=tx_data[1])
        date_entry = ctk.CTkEntry(dialog, textvariable=date_var)
        date_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        ctk.CTkLabel(dialog, text="Type:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        type_var = ctk.StringVar(value=tx_data[2])
        type_menu = ctk.CTkOptionMenu(dialog, values=["income", "expense"], variable=type_var)
        type_menu.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        ctk.CTkLabel(dialog, text="Category:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        # Use appropriate categories based on current type
        category_var = ctk.StringVar(value=tx_data[3])
        def update_category_options(*args):
            values = config.INCOME_CATEGORIES if type_var.get() == "income" else config.EXPENSE_CATEGORIES
            category_menu.configure(values=values)
            # If current value not in list, set first value
            if category_var.get() not in values:
                category_var.set(values[0])
        category_menu = ctk.CTkOptionMenu(dialog, values=config.INCOME_CATEGORIES if tx_data[2] == "income" else config.EXPENSE_CATEGORIES, variable=category_var)
        category_menu.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        # Trace type var to update categories when changed
        type_var.trace_add("write", lambda *args: update_category_options())
        ctk.CTkLabel(dialog, text="Amount:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        amount_var = ctk.StringVar(value=str(tx_data[4]))
        amount_entry = ctk.CTkEntry(dialog, textvariable=amount_var)
        amount_entry.grid(row=3, column=1, padx=10, pady=5, sticky="ew")
        ctk.CTkLabel(dialog, text="Note:").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        note_var = ctk.StringVar(value=tx_data[5] or "")
        note_entry = ctk.CTkEntry(dialog, textvariable=note_var)
        note_entry.grid(row=4, column=1, padx=10, pady=5, sticky="ew")
        def save_changes() -> None:
            # Validate date and amount
            try:
                datetime.strptime(date_var.get(), "%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Invalid Date", "Please enter a valid date (YYYY-MM-DD).")
                return
            try:
                amt = float(amount_var.get())
            except ValueError:
                messagebox.showerror("Invalid Amount", "Amount must be numeric.")
                return
            database.update_transaction(
                tx_id,
                date=date_var.get(),
                ttype=type_var.get(),
                category=category_var.get(),
                amount=amt,
                note=note_var.get(),
            )
            dialog.destroy()
            self.refresh_dashboard()
        ctk.CTkButton(dialog, text="Save", command=save_changes).grid(row=5, column=0, columnspan=2, pady=15)

    def confirm_delete_transaction(self, tx_id: int) -> None:
        """Prompt the user to confirm deletion of a transaction."""
        if messagebox.askyesno("Delete Transaction", "Are you sure you want to delete this transaction?"):
            database.delete_transaction(tx_id)
            self.refresh_dashboard()

    def create_analysis_dialog(self):
        # Unused stub (not used in version 3)
        pass

    # end of App class

if __name__ == "__main__":
    app = App()
    app.mainloop()