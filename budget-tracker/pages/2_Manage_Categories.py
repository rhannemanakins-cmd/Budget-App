import streamlit as st
import psycopg2
from psycopg2 import errors
import pandas as pd

st.set_page_config(page_title="Manage Categories", layout="wide")

# 1. Connect to the database using st.secrets (Rubric Requirement!)
@st.cache_resource
def init_connection():
    return psycopg2.connect(st.secrets["DB_URL"])

conn = init_connection()

# 2. Initialize Database Tables
def init_db():
    with conn.cursor() as cur:
        # Create tables if they don't exist
        cur.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                transaction_date DATE NOT NULL DEFAULT CURRENT_DATE,
                payee_or_source VARCHAR(100) NOT NULL,
                total_amount NUMERIC(10,2) NOT NULL,
                notes TEXT
            );
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50) NOT NULL UNIQUE,
                type VARCHAR(20) NOT NULL,
                target_amount NUMERIC(10,2) DEFAULT 0,
                target_date DATE
            );
            CREATE TABLE IF NOT EXISTS transaction_splits (
                id SERIAL PRIMARY KEY,
                transaction_id INTEGER REFERENCES transactions(id) ON DELETE CASCADE,
                category_id INTEGER REFERENCES categories(id) ON DELETE RESTRICT,
                amount NUMERIC(10,2) NOT NULL
            );
        """)
        conn.commit()

# Run the initialization
init_db()

st.title("Manage Categories")

col1, col2 = st.columns([1, 2])

# 3. Create Form (Create Operation & Validation)
with col1:
    st.subheader("Add New Category")
    with st.form("add_category_form"):
        name = st.text_input("Category Name *")
        cat_type = st.selectbox("Type *", ["Income", "Expense", "Savings Goal"])
        target_amount = st.number_input("Target Amount / Budget Limit ($) *", min_value=0.0, step=10.0)
        target_date = st.date_input("Target Date (Optional for Savings)", value=None)
        
        submitted = st.form_submit_button("Save Category")
        
        if submitted:
            # Validation Rule: No blanks
            if not name.strip():
                st.error("Category Name is required.")
            else:
                try:
                    with conn.cursor() as cur:
                        # Parameterized query to prevent SQL injection
                        cur.execute(
                            """INSERT INTO categories (name, type, target_amount, target_date) 
                               VALUES (%s, %s, %s, %s)""", 
                            (name.strip(), cat_type, target_amount, target_date)
                        )
                        conn.commit()
                    st.success(f"Category '{name}' added successfully!")
                    st.rerun() # Refresh the page to update the table
                except errors.UniqueViolation:
                    conn.rollback()
                    st.error(f"A category named '{name}' already exists.")
                except Exception as e:
                    conn.rollback()
                    st.error(f"Database Error: {e}")

# 4. Read Data & 5. Delete Functionality
with col2:
    st.subheader("Current Categories")
    
    # Read operation
    df = pd.read_sql("SELECT id, name, type, target_amount, target_date FROM categories ORDER BY type, name", conn)
    
    if df.empty:
        st.info("No categories found. Create one using the form on the left.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.write("---")
        st.subheader("Delete a Category")
        
        # Delete operation with dynamic dropdown
        cat_to_delete = st.selectbox("Select Category to Delete", df['name'].tolist())
        
        if st.button("Delete Selected Category"):
            try:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM categories WHERE name = %s", (cat_to_delete,))
                    conn.commit()
                st.success(f"Deleted category '{cat_to_delete}'.")
                st.rerun()
            except errors.ForeignKeyViolation:
                conn.rollback()
                st.error(f"Cannot delete '{cat_to_delete}' because it is currently tied to a transaction.")
            except Exception as e:
                conn.rollback()
                st.error(f"Database Error: {e}")