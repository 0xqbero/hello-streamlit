import streamlit as st

tops_df = st.session_state.df

for symbol in tops_df['Symbol']:
    print(symbol)