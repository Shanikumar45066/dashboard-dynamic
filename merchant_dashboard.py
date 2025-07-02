import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Merchant Performance Dashboard", layout="wide")

st.title("📊 Dynamic Merchant Performance Dashboard")

# Upload files
uploaded_file_1 = st.file_uploader("Upload Matching File (AM & Merchant ID)", type=["csv", "xlsx"])
uploaded_file_2 = st.file_uploader("Upload Base Data (Previous Month)", type=["csv", "xlsx"])
uploaded_file_3 = st.file_uploader("Upload Current Data (This Month)", type=["csv", "xlsx"])

def read_file(file):
    if file.name.endswith('.csv'):
        return pd.read_csv(file)
    else:
        return pd.read_excel(file)

# Load available files
df_match = read_file(uploaded_file_1) if uploaded_file_1 else None
df_base = read_file(uploaded_file_2) if uploaded_file_2 else None
df_current = read_file(uploaded_file_3) if uploaded_file_3 else None

if df_base is not None and df_current is not None:
    st.subheader("🔍 Merging & Comparing Data")

    key = 'client_id'
    df_base.rename(columns=lambda x: x.strip(), inplace=True)
    df_current.rename(columns=lambda x: x.strip(), inplace=True)

    df_compare = pd.merge(df_base, df_current, on=key, suffixes=('_base', '_current'))

    if df_match is not None:
        df_match.rename(columns=lambda x: x.strip(), inplace=True)
        df_compare = pd.merge(df_compare, df_match, on=key, how='left')

    # Define fields to compare
    fields_to_compare = ['success_txn', 'failed_txn', 'abort_init_txn', 'refunded_txn',
                         'refund_init_txn', 'total_txn', 'TSR', 'paidamount', 'payeeamount']

    for field in fields_to_compare:
        base_col = f"{field}_base"
        current_col = f"{field}_current"
        change_col = f"{field} Change %"
        if base_col in df_compare.columns and current_col in df_compare.columns:
            df_compare[change_col] = np.where(df_compare[base_col] != 0,
                                              ((df_compare[current_col] - df_compare[base_col]) / df_compare[base_col]) * 100,
                                              np.nan)

    # Categorization based on paidamount
    df_compare['Performance Tag'] = np.where(df_compare['paidamount Change %'] > 20, 'High Performing',
                                    np.where(df_compare['paidamount Change %'] < -20, 'At Risk', 'Stable'))

    # Filters
    st.sidebar.subheader("📌 Filters")
    am_list = df_compare['Account Manager'].dropna().unique() if 'Account Manager' in df_compare.columns else []
    selected_am = st.sidebar.selectbox("Select Account Manager", ['All'] + list(am_list))

    if selected_am != 'All':
        df_compare = df_compare[df_compare['Account Manager'] == selected_am]

    st.subheader("📈 Summary Metrics")
    col1, col2, col3 = st.columns(3)
    col1.metric("📦 Total Merchants", df_compare.shape[0])
    col2.metric("📈 High Performing", (df_compare['Performance Tag'] == 'High Performing').sum())
    col3.metric("⚠️ At Risk", (df_compare['Performance Tag'] == 'At Risk').sum())

    # Charts
    fig1 = px.bar(df_compare, x='client_name', y='paidamount Change %', color='Performance Tag',
                  title='GMV (Paid Amount) Change % by Merchant')
    st.plotly_chart(fig1, use_container_width=True)

    fig2 = px.pie(df_compare, names='Performance Tag', title='Merchant Categorization')
    st.plotly_chart(fig2, use_container_width=True)

    # Display data
    st.subheader("📋 Merchant Details Table")
    st.dataframe(df_compare)

    # Export CSV
    csv_export = df_compare.to_csv(index=False)
    st.download_button("⬇️ Download Full Report", csv_export, "merchant_performance_report.csv", "text/csv")

else:
    st.info("Please upload at least Base Data and Current Data files to begin comparison.")
