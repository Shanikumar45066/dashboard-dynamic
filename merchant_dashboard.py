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

def map_column(columns, aliases):
    for alias in aliases:
        for col in columns:
            if alias in col:
                return col
    return None

# Load available files
df_match = read_file(uploaded_file_1) if uploaded_file_1 else None
df_base = read_file(uploaded_file_2) if uploaded_file_2 else None
df_current = read_file(uploaded_file_3) if uploaded_file_3 else None

if df_base is not None and df_current is not None:
    st.subheader("🔍 Merging & Comparing Data")

    # Clean column names
    df_base.columns = df_base.columns.str.strip().str.lower()
    df_current.columns = df_current.columns.str.strip().str.lower()
    if df_match is not None:
        df_match.columns = df_match.columns.str.strip().str.lower()

    # Define possible key names
    possible_keys = ['merchant id', 'client code', 'client_id', 'client code', 'clientid', 'mid']
    common_keys = [col for col in df_base.columns if col in df_current.columns and col in possible_keys]
    if not common_keys:
        st.error("❌ No common key (e.g. 'client code', 'merchant id') found in both Base and Current Data.")
        st.stop()

    key = common_keys[0]
    st.info(f"✅ Using '{key}' as the key column for merging data.")

    # Merge base and current data
    df_compare = pd.merge(df_base, df_current, on=key, suffixes=('_base', '_current'))

    if df_match is not None and key in df_match.columns:
        df_compare = pd.merge(df_compare, df_match[[key] + [col for col in df_match.columns if col != key]], on=key, how='left')

    # Alias mappings
    txn_aliases = ['transaction count', 'txn_count', 'total transactions', 'success_txn']
    gmv_aliases = ['gmv', 'paidamount', 'total amount', 'amount']
    success_aliases = ['successful transactions', 'success_txn', 'txn success', 'successful']

    txn_base_col = map_column(df_compare.columns, [alias + '_base' for alias in txn_aliases])
    txn_current_col = map_column(df_compare.columns, [alias + '_current' for alias in txn_aliases])
    gmv_base_col = map_column(df_compare.columns, [alias + '_base' for alias in gmv_aliases])
    gmv_current_col = map_column(df_compare.columns, [alias + '_current' for alias in gmv_aliases])
    success_col = map_column(df_compare.columns, [alias + '_current' for alias in success_aliases])

    if not all([txn_base_col, txn_current_col, gmv_base_col, gmv_current_col, success_col]):
        st.error("❌ Ensure 'Transaction Count', 'GMV', and 'Successful Transactions' columns are present (even under alternative names).")
        st.stop()

    # Add calculated columns
    df_compare['txn growth %'] = ((df_compare[txn_current_col] - df_compare[txn_base_col]) / df_compare[txn_base_col]) * 100
    df_compare['gmv growth %'] = ((df_compare[gmv_current_col] - df_compare[gmv_base_col]) / df_compare[gmv_base_col]) * 100
    df_compare['tsr_current'] = df_compare[success_col] / df_compare[txn_current_col]

    # Performance classification
    def classify_stage(growth):
        if growth > 100:
            return 'High Performing'
        elif growth < 80:
            return 'Low Performing'
        elif 90 <= growth <= 99:
            return 'On Track'
        else:
            return 'Stable'

    df_compare['performance stage'] = df_compare['gmv growth %'].apply(classify_stage)

    # Filters
    st.sidebar.subheader("📌 Filters")
    am_list = df_compare['account manager'].dropna().unique() if 'account manager' in df_compare.columns else []
    selected_am = st.sidebar.selectbox("Select Account Manager", ['All'] + list(am_list))

    if selected_am != 'All':
        df_compare = df_compare[df_compare['account manager'] == selected_am]

    # Summary Metrics
    st.subheader("📈 Summary Metrics")
    total_merchants = df_compare.shape[0]
    total_success_txns = df_compare[success_col].sum()
    total_txns = df_compare[txn_current_col].sum()
    tsr = (total_success_txns / total_txns) * 100 if total_txns > 0 else 0
    total_gmv = df_compare[gmv_current_col].sum()
    on_track = (df_compare['performance stage'] == 'On Track').sum()
    high_perf = (df_compare['performance stage'] == 'High Performing').sum()
    low_perf = (df_compare['performance stage'] == 'Low Performing').sum()

    col1, col2, col3 = st.columns(3)
    col1.metric("📦 Total Merchants", total_merchants)
    col2.metric("✅ Total Successful Txns", int(total_success_txns))
    col3.metric("📊 TSR (%)", round(tsr, 2))

    col4, col5, col6 = st.columns(3)
    col4.metric("💰 Total GMV", f"{total_gmv:,.2f}")
    col5.metric("📈 High Performing", high_perf)
    col6.metric("🟡 On Track", on_track)

    st.metric("🔻 Low Performing", low_perf)

    # Charts
    st.subheader("📊 Merchant Performance Categorization")
    fig_stage = px.pie(df_compare, names='performance stage', title='Merchant Categorization by GMV Growth Stage')
    st.plotly_chart(fig_stage, use_container_width=True)

    # Table & Export
    st.subheader("📋 Merchant Details Table")
    st.dataframe(df_compare)

    csv_export = df_compare.to_csv(index=False)
    st.download_button("⬇️ Download Full Report", csv_export, "merchant_performance_report.csv", "text/csv")

else:
    st.info("Please upload at least Base Data and Current Data files to begin comparison.")
