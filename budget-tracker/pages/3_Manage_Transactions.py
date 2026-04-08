import streamlit as st
import psycopg2
import pandas as pd
import datetime

st.set_page_config(page_title="Manage Transactions", layout="wide")

# 1. Connect to the Database
@st.cache_resource
def init_connection():
    return psycopg2.connect(st.secrets["DB_URL"])

conn = init_connection()

st.title("Manage Transactions")

# 2. Fetch Categories for Dynamic Dropdowns (Rubric Requirement)
def get_categories():
    with conn.cursor() as cur:
        cur.execute("SELECT id, name FROM categories ORDER BY name;")
        rows = cur.fetchall()
        # Create a dictionary mapping Name -> ID (e.g., {"Groceries": 1})
        return {row[1]: row[0] for row in rows}

cat_dict = get_categories()

if not cat_dict:
    st.warning("⚠️ You need to create at least one Category before you can add a transaction!")
    st.stop() # Stops the rest of the page from loading until they make a category

# --- Setup Dynamic Splits using Session State ---
if 'split_count' not in st.session_state:
    st.session_state.split_count = 1

def add_split():
    st.session_state.split_count += 1

col1, col2 = st.columns([1, 1.5])

# --- LEFT COLUMN: Create Transaction Form ---
with col1:
    st.subheader("Add New Transaction")
    
    # Parent Transaction Inputs
    t_date = st.date_input("Transaction Date", value=datetime.date.today())
    payee = st.text_input("Payee / Source *")
    total_amount = st.number_input("Total Amount ($) *", min_value=0.0, step=1.0)
    notes = st.text_area("Notes (Optional)")
    
    st.write("---")
    st.write("**Split this transaction across categories:**")
    
    # Dynamic Split Inputs
    splits_data = []
    split_total = 0.0
    
    for i in range(st.session_state.split_count):
        scol1, scol2 = st.columns([2, 1])
        with scol1:
            cat_name = st.selectbox(f"Category {i+1}", options=list(cat_dict.keys()), key=f"cat_{i}")
        with scol2:
            amt = st.number_input(f"Amount {i+1} ($)", min_value=0.0, step=1.0, key=f"amt_{i}")
        
        # Store the data from this row
        splits_data.append({"cat_id": cat_dict[cat_name], "amount": amt})
        split_total += amt

    # Button to add more split rows
    st.button("➕ Add Another Category Split", on_click=add_split)
    
    st.write("---")
    
    # Submit Button & Validation
    if st.button("💾 Save Transaction", type="primary"):
        errors = []
        
        # Validation Rules (Rubric Requirement)
        if not payee.strip():
            errors.append("Payee is required.")
        if total_amount <= 0:
            errors.append("Total Amount must be greater than 0.")
        if round(split_total, 2) != round(total_amount, 2):
            errors.append(f"Math Error: Your splits add up to ${split_total:.2f}, but the Total Amount is ${total_amount:.2f}. They must match exactly!")
            
        if errors:
            for err in errors:
                st.error(err)
        else:
            try:
                with conn.cursor() as cur:
                    # Insert Parent Transaction & get the new ID back
                    cur.execute(
                        """INSERT INTO transactions (transaction_date, payee_or_source, total_amount, notes) 
                           VALUES (%s, %s, %s, %s) RETURNING id;""",
                        (t_date, payee.strip(), total_amount, notes.strip())
                    )
                    new_txn_id = cur.fetchone()[0]
                    
                    # Loop through splits and insert each one
                    for split in splits_data:
                        if split["amount"] > 0: # Only save splits that actually have money
                            cur.execute(
                                """INSERT INTO transaction_splits (transaction_id, category_id, amount) 
                                   VALUES (%s, %s, %s);""",
                                (new_txn_id, split["cat_id"], split["amount"])
                            )
                    
                    # Commit the entire transaction
                    conn.commit()
                
                st.success("Transaction saved successfully!")
                st.session_state.split_count = 1 # Reset the splits back to 1 row
                st.rerun()
                
            except Exception as e:
                conn.rollback()
                st.error(f"Database Error: {e}")

# --- RIGHT COLUMN: Read, Search & Delete ---
with col2:
    st.subheader("Transaction History")
    
    # Search / Filter (Rubric Requirement)
    search_term = st.text_input("🔍 Search by Payee")
    
    # Query Database
    if search_term:
        query = """SELECT id, transaction_date, payee_or_source, total_amount, notes 
                   FROM transactions WHERE payee_or_source ILIKE %s ORDER BY transaction_date DESC"""
        df = pd.read_sql(query, conn, params=(f"%{search_term}%",))
    else:
        df = pd.read_sql("SELECT id, transaction_date, payee_or_source, total_amount, notes FROM transactions ORDER BY transaction_date DESC", conn)
    
    if df.empty:
        st.info("No transactions found.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.write("---")
        st.subheader("Delete a Transaction")
        
        # Create a user-friendly dropdown for deletion
        # Formats like: "ID 5: Target ($100.00)"
        df['display_name'] = "ID " + df['id'].astype(str) + ": " + df['payee_or_source'] + " ($" + df['total_amount'].astype(str) + ")"
        txn_to_delete = st.selectbox("Select Transaction to Delete", df['display_name'].tolist())
        
        # Confirmation Checkbox (Rubric Requirement)
        confirm = st.checkbox("I understand that deleting this will also delete its category splits.")
        
        if st.button("Delete Selected Transaction"):
            if confirm:
                try:
                    # Extract the ID from the string (e.g., getting '5' out of "ID 5: Target...")
                    t_id = int(txn_to_delete.split(":")[0].replace("ID ", ""))
                    
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM transactions WHERE id = %s", (t_id,))
                        conn.commit()
                    st.success("Transaction deleted!")
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"Database Error: {e}")
            else:
                st.warning("Please check the confirmation box before deleting.")