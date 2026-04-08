import streamlit as st
import psycopg2
import pandas as pd
import datetime
import calendar

st.set_page_config(page_title="Financial Dashboard", layout="wide")

# 1. Connect to the Database
@st.cache_resource
def init_connection():
    return psycopg2.connect(st.secrets["DB_URL"])

try:
    conn = init_connection()
except Exception as e:
    st.error(f"Could not connect to database: {e}")
    st.stop()

st.title("📊 Financial Dashboard")

# --- DATE FILTER (Rubric Requirement: Filter Feature) ---
st.write("### Filter Dashboard by Date")

# Default to the current month
today = datetime.date.today()
first_day = today.replace(day=1)
last_day = today.replace(day=calendar.monthrange(today.year, today.month)[1])

col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    start_date = st.date_input("Start Date", value=first_day)
with col2:
    end_date = st.date_input("End Date", value=last_day)

if start_date > end_date:
    st.error("Start Date must be before End Date.")
    st.stop()

st.write("---")

# --- FETCH METRICS DATA (Rubric Requirement: Summary Counts) ---
def get_total_by_type(cat_type, start, end):
    query = """
        SELECT COALESCE(SUM(ts.amount), 0) 
        FROM transaction_splits ts
        JOIN categories c ON ts.category_id = c.id
        JOIN transactions t ON ts.transaction_id = t.id
        WHERE c.type = %s AND t.transaction_date >= %s AND t.transaction_date <= %s;
    """
    with conn.cursor() as cur:
        cur.execute(query, (cat_type, start, end))
        return cur.fetchone()[0]

# Calculate totals
total_income = get_total_by_type('Income', start_date, end_date)
total_expense = get_total_by_type('Expense', start_date, end_date)
net_cash_flow = total_income - total_expense

# --- DISPLAY METRICS ---
m1, m2, m3 = st.columns(3)
m1.metric("Total Income", f"${total_income:,.2f}")
m2.metric("Total Expenses", f"${total_expense:,.2f}")
m3.metric("Net Cash Flow", f"${net_cash_flow:,.2f}", delta=float(net_cash_flow))

st.write("---")

# --- BUDGET VS ACTUAL TABLE ---
st.write("### 📉 Expense Budget vs. Actual Spending")

# Query to compare targets to actual spending within the date range
budget_query = """
    SELECT 
        c.name AS "Category",
        c.target_amount AS "Budget Limit",
        COALESCE(SUM(ts.amount), 0) AS "Actual Spent"
    FROM categories c
    LEFT JOIN transaction_splits ts ON c.id = ts.category_id
    LEFT JOIN transactions t ON ts.transaction_id = t.id 
        AND t.transaction_date >= %s AND t.transaction_date <= %s
    WHERE c.type = 'Expense'
    GROUP BY c.id, c.name, c.target_amount
    ORDER BY "Category";
"""

df_budgets = pd.read_sql(budget_query, conn, params=(start_date, end_date))

if df_budgets.empty:
    st.info("No expense categories found. Go to 'Manage Categories' to set up your budget.")
else:
    # Calculate Remaining Budget
    df_budgets["Remaining"] = df_budgets["Budget Limit"] - df_budgets["Actual Spent"]
    
    # Format as currency for display
    for col in ["Budget Limit", "Actual Spent", "Remaining"]:
        df_budgets[col] = df_budgets[col].apply(lambda x: f"${x:,.2f}")
        
    st.dataframe(df_budgets, use_container_width=True, hide_index=True)

st.write("---")

# --- SAVINGS GOALS PROGRESS ---
st.write("### 🏦 Savings Goals")

savings_query = """
    SELECT 
        c.name AS "Goal Name",
        c.target_amount AS "Target Goal",
        COALESCE(SUM(ts.amount), 0) AS "Amount Saved",
        c.target_date AS "Target Date"
    FROM categories c
    LEFT JOIN transaction_splits ts ON c.id = ts.category_id
    WHERE c.type = 'Savings Goal'
    GROUP BY c.id, c.name, c.target_amount, c.target_date
    ORDER BY "Target Date" ASC;
"""
# Notice we don't filter savings by date! Savings usually accumulate forever until the goal is hit.
df_savings = pd.read_sql(savings_query, conn)

if df_savings.empty:
    st.info("No savings goals set up yet.")
else:
    # Calculate progress percentage safely
    df_savings["Progress %"] = (df_savings["Amount Saved"] / df_savings["Target Goal"]) * 100
    df_savings["Progress %"] = df_savings["Progress %"].fillna(0).clip(upper=100).apply(lambda x: f"{x:.1f}%")
    
    for col in ["Target Goal", "Amount Saved"]:
        df_savings[col] = df_savings[col].apply(lambda x: f"${x:,.2f}")
        
    st.dataframe(df_savings, use_container_width=True, hide_index=True)