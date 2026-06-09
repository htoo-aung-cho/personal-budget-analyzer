# Personal Budget Analyzer and Income‑Expense Tracker — Version 3

## Overview

This project is a desktop application written in Python for a
university Operating Systems course.  It demonstrates how an
agent‑like program can observe data, analyse it, make simple
decisions and act upon them.  Version 3 extends the original
assignment by supporting **multiple independent budget trackers** and
adding the ability to **edit** or **delete** transactions after
they are created.  Each tracker can operate in either a fixed
monthly budget mode or a balance tracking mode, and the user can
switch between trackers at any time.

The software uses
[CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) for
the user interface and SQLite for local data storage.  All data is
stored on your machine; no network connection is required.

## Features

### Trackers

* **Multiple trackers**: Create as many budget trackers as you like — for
  example, one for personal expenses and another for restaurant
  spending.  Each tracker maintains its own income and expense
  records and configuration.
* **Tracker management**: List, open and delete existing trackers.  The
  management page also provides a form for creating a new tracker
  complete with its name, mode and optional starting values.
* **Edit tracker settings**: Change a tracker's name, switch its
  tracking mode and adjust its monthly budget or starting balance from
  the Settings page.

### Transactions

* **Income and expense logging**: Record transactions with a date,
  category, amount and optional note.  Categories come from
  configurable lists in `config.py`.
* **Edit and delete transactions**: Use the Edit button next to any
  transaction to update its details or the Delete button to remove it
  entirely.

### Modes

* **Monthly Budget Mode**: Specify a fixed monthly spending limit.  The
  dashboard shows how much of the budget has been used in the current
  month and warns when you exceed 80 %.
* **Balance Tracking Mode**: Enter a starting balance.  Your balance
  is updated based on income and expenses.

### Dashboard and Analysis

* **Summary cards**: See total income, total expenses, remaining
  balance and budget usage at a glance.
* **Recent transactions**: A scrollable table lists the most recent
  transactions with edit/delete actions.
* **Analysis**: View top earning and spending categories and a bar
  chart showing expense distribution by category.  The analysis
  updates automatically when transactions change.

### Agentic alerts

The application monitors your data and provides helpful warnings:

* When more than 80 % of your monthly budget is used.
* When expenses exceed income.
* When a particular category dominates your spending.

### OS Concepts

| OS Concept            | Project Demonstration                                                  |
|-----------------------|------------------------------------------------------------------------|
| **File management**   | Transaction data is stored locally in an SQLite database file.         |
| **Process automation**| The app automatically recalculates summaries and alerts whenever data  |
|                       | changes, illustrating how software can react to events without user    |
|                       | input.                                                                 |
| **User interaction**  | A desktop UI built with CustomTkinter provides interactive forms and   |
|                       | navigation.                                                            |
| **Data storage**      | A lightweight relational database (SQLite) persists information across |
|                       | sessions.                                                              |
| **System workflow**   | The application follows a clear pipeline: input → process/analysis →   |
|                       | output.                                                                |
| **Resource use**      | All computation is local, uses minimal memory and CPU, and requires no |
|                       | network access.                                                        |

## Installation

1. **Download or clone the project**: Place the `personal_budget_agent_v3`
   folder on your computer.
2. **Create a virtual environment** (recommended):

   ```bash
   cd personal_budget_agent_v3
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**:

   ```bash
   python3 main.py
   ```

## Usage Tips

* **Selecting trackers**: The first screen lists all trackers.  Click
  **Open** to work with a tracker or **Delete** to remove it.  Use
  **Create New Tracker** to set up a new one.
* **Multiple budgets**: Feel free to create trackers for different
  purposes (e.g. "Personal", "Restaurant", "Shopping").  Each tracker
  keeps its own data and settings.
* **Editing transactions**: On the dashboard, click **Edit** to
  modify a transaction or **Del** to remove it.  Changes take effect
  immediately.
* **Changing settings**: Use the Settings page to rename the tracker,
  switch modes or update budgets.  You can return to the tracker
  selection screen from the Settings page at any time.

## For macOS Users

On macOS, the built‑in Python may be outdated.  Ensure you install
Python 3 via [Homebrew](https://brew.sh/) or from
[python.org](https://www.python.org/downloads/), then follow the
installation steps above.  When running the program, macOS might
prevent the opening of applications downloaded from the internet; if
you encounter a security dialog, open System Preferences → Security &
Privacy and allow the program to run.

## About

This project was developed as an educational assignment for an
Operating Systems course.  It is not intended to replace
professional financial software but serves as a hands‑on example of
how Python applications can manage local data, provide a user
interface and implement simple agentic behaviours.