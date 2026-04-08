# Personal Finance & Budget Tracker

## Project Overview
This system is a personal finance tracker designed for individuals who want a simple way to monitor their daily income and expenses against budgeted goals. The user logs each transaction (tracking the date, payee, and total amount) and manages a custom list of budget categories (such as "Groceries," "Rent," or "Savings Goals"). To handle real-world spending, the system specifically tracks "split transactions," allowing the user to divide a single receipt across multiple categories. Ultimately, the system tracks where money is being spent and provides a clear summary of cash flow.

## Live Application
**[Link to Live Streamlit App]**(Put your Streamlit Cloud URL here once deployed)

## Entity-Relationship Diagram (ERD)
![Database ERD](erd.png)

## Database Tables
This application uses a PostgreSQL database with three tables to satisfy the many-to-many relationship requirement:

1. **`transactions`**: The "Actuals." Logs every time money moves in or out, tracking the date, payee, and total amount of the receipt or income.
2. **`categories`**: The "Plan." Holds user-defined income types, monthly expense budgets, and future savings goals.
3. **`transaction_splits`**: The Junction Table. This bridges the actual transactions and the planned categories, allowing a single transaction to be split across multiple different budget categories.

## How to Run Locally

If you want to run this application on your own machine, follow these steps:

1. **Clone the repository** to your local machine.
2. **Install the required dependencies** via terminal:
   ```bash
   python -m pip install streamlit psycopg2-binary pandas