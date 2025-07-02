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

    # Clean column names
    df_base.columns = df_base.columns.str.strip().str.lower()
    df_current.columns = df_current.columns.str.strip().str.lower()
    if df_match is not None:
        df_match.columns = df_match.columns.str.strip().str.lower()

    # Define possible key names
    possible_keys = ['merchant id', 'client code', 'client_id', 'client code', 'clientid', 'mid']

    # Find common keys
    common_keys = [col for col in df_base.columns if col in df_current.columns and col in possible_keys]
    if not common_keys:
        st.error("❌ No common key (e.g. 'client code', 'merchant id') found in both Base and Current Data.")
        st.stop()

    key = common_keys[0]  # Pick first matching key
    st.info(f"✅ Using '{key}' as the key column for merging data.")

    # Merge base and current data
    df_compare = pd.merge(df_base, df_current, on=key, suffixes=('_base', '_current'))

    # Merge match file if available
    if df_match is not None and key in df_match.columns:
        df_compare = pd.merge(df_compare, df_match[[key] + [col for col in df_match.columns if col != key]], on=key, how='left')

    # Calculate % Change
    try:
        df_compare['txn growth %'] = ((df_compare['transaction count_current'] - df_compare['transaction count_base']) / df_compare['transaction count_base']) * 100
        df_compare['gmv growth %'] = ((df_compare['gmv_current'] - df_compare['gmv_base']) / df_compare['gmv_base']) * 100
    except KeyError:
        st.error("❌ Please ensure both Base and Current files have 'transaction count' and 'gmv' columns.")
        st.stop()

    # Categorization
    df_compare['performance tag'] = np.where(df_compare['gmv growth %'] > 20, 'High Performing',
                                    np.where(df_compare['gmv growth %'] < -20, 'At Risk', 'Stable'))

    # Filters
    st.sidebar.subheader("📌 Filters")
    am_list = df_compare['account manager'].dropna().unique() if 'account manager' in df_compare.columns else []
    selected_am = st.sidebar.selectbox("Select Account Manager", ['All'] + list(am_list))

    if selected_am != 'All':
        df_compare = df_compare[df_compare['account manager'] == selected_am]

    st.subheader("📈 Summary Metrics")
    col1, col2, col3 = st.columns(3)
    col1.metric("📦 Total Merchants", df_compare.shape[0])
    col2.metric("📈 High Performing", (df_compare['performance tag'] == 'High Performing').sum())
    col3.metric("⚠️ At Risk", (df_compare['performance tag'] == 'At Risk').sum())

    # Charts
    fig1 = px.bar(df_compare, x=key, y='gmv growth %', color='performance tag', title='GMV Growth % by Merchant')
    st.plotly_chart(fig1, use_container_width=True)

    fig2 = px.pie(df_compare, names='performance tag', title='Merchant Categorization')
    st.plotly_chart(fig2, use_container_width=True)

    # Display data
    st.subheader("📋 Merchant Details Table")
    st.dataframe(df_compare)

    # Export CSV
    csv_export = df_compare.to_csv(index=False)
    st.download_button("⬇️ Download Full Report", csv_export, "merchant_performance_report.csv", "text/csv")

else:
    st.info("Please upload at least Base Data and Current Data files to begin comparison.")
