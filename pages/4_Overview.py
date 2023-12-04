# Import libraries
import pandas as pd
import streamlit as st
import plotly.express as px
import requests
from bs4 import BeautifulSoup
import datetime
import numpy as np
import plotly.graph_objects as go
import re

st.set_page_config(page_title="Insider Collective",
                   page_icon=":bar_chart:",
                   layout="wide"
)

# - - - - FETCHING DATA AND CREATING DATAFRAME - - - -

@st.cache_data(ttl=28800)
def load_data():
    #Set parameters: Select minimum transaction value and timeframe (d, w, m)
    min_transaction = 25000
    timeframe = 'q'

    # Define the list of URLs to loop through
    url_template = 'https://www.dataroma.com/m/ins/ins.php?t=' + str(timeframe) +'&po=1' '&am=' + str(min_transaction) + '&sym=&o=fd&d=d&L={}'

    # Initialize an empty list to store the DataFrames
    df_list = []

    for i in range(1, 30):
        # Generate the URL with the loop variable
        url = url_template.format(i)

        # Make the request and get the HTML content
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:105.0) Gecko/20100101 Firefox/105.0'}
        r = requests.get(url, headers=headers)
        html = r.content

        # Get the third DataFrame object from the list
        df = pd.read_html(html)[2]

        # Append the DataFrame to the list
        df_list.append(df)

    # Concatenate all the DataFrames into a single DataFrame
    df = pd.concat(df_list, ignore_index=True)

    # Renaming columns with more user-friendly names
    df.columns = ['Filing', 'Symbol', 'Security', 'Insider name', 'Relationship', 'Transaction date', 'Type', 'Shares', 'Price', 'Amount', 'D/I']

    
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')

    # Clean "Relationship" column

    # Crear una función para asignar el rol correcto
    def get_role(relationship):
        if re.search(r"ceo|chief executive officer", relationship.lower()):
            return "CEO"
        elif re.search(r"cfo|chief financial officer", relationship.lower()):
            return "CFO"
        elif re.search(r"chief|^c\w+o", relationship.lower()):
            return "Other C-level"
        elif re.search(r"director", relationship.lower()):
            return "Director"
        elif re.search(r"president", relationship.lower()):
            return "President"
        elif re.search(r"10%", relationship.lower()):
            return "Shareholder (10%+)"
        elif re.search(r"evp|svp", relationship.lower()):
            return "Executive/Senior VP"
        else:
            return "Other"

    # Agregar la nueva columna
    df["Role"] = df["Relationship"].apply(get_role)

    return(df)

df=load_data()

# - - - - SIDEBAR - - - -

st.sidebar.header('Filters:')

# DATES

df['Filing'] = pd.to_datetime(df['Filing'])

start_date = st.sidebar.date_input(
    'Start date', datetime.date.today() - datetime.timedelta(days=10)
)
end_date = st.sidebar.date_input(
    'End date', datetime.date.today()
)

# Convert date_input values to datetime64[ns]
start_date = pd.to_datetime(start_date)
end_date = pd.to_datetime(end_date)

# ROLES

roles_of_interest = st.sidebar.multiselect("Roles", ["CEO", "CFO", "Director", "10%", "President", "SVP"])

# TICKER SYMBOL

ticker = st.sidebar.multiselect("Ticker symbol", df["Symbol"].unique())

# Create a boolean condition for filtering
date_condition = (df['Filing'] >= start_date) & (df['Filing'] <= end_date)
roles_condition = df['Relationship'].str.contains('|'.join(roles_of_interest))
ticker_condition = df['Symbol'].str.contains('|'.join(ticker))

filtered_df = df[date_condition & roles_condition & ticker_condition]

# - - - - MAINPAGE - - - -

st.title('Insider Collective')
st.markdown('#### Unlock the power of insider knowledge')
st.markdown('Insiders might sell their shares for any number of reasons, but they buy them for only one: they think the price will rise. Elevate your investment strategy with our dynamic interactive dashboard, empowering you to pinpoint key insider purchase trends for informed and strategic decision-making.')
st.markdown('##')

# Top KPIs

total_purchases = int(filtered_df['Amount'].sum())
median_purchase = int(filtered_df['Amount'].median())
n_companies = len(filtered_df['Symbol'].unique())

l, m, r = st.columns(3)

with l:
    st.markdown("**Total purchase volume**")
    st.markdown("US "+"${:,.0f}".format(total_purchases))
with m:
    st.markdown("**Median transaction**")
    st.markdown("US "+"${:,.0f}".format(median_purchase))
with r:
    st.markdown("**Number of companies**")
    st.markdown(n_companies)

st.markdown("---")

# Top 10 chart

top_10 = (
    filtered_df.groupby(['Symbol'])['Amount'].sum().sort_values(ascending=False).nlargest(20)
)

fig_top10 = px.bar(
    top_10,
    x=top_10.index,
    y="Amount",
    title = "Title of the chart",
    color_discrete_sequence = ["#04b73c"] * len(top_10),
    template = "plotly_white",
)

st.plotly_chart(fig_top10, use_container_width=True)

# Insider breakdown chart

role_color_map = {'CEO': '#596689', 
                  'CFO': '#6C8976', 
                  'Other C-level': '#79b791', 
                  'Director' : '#abd1b5',
                  'President' : '#bfbf96',
                  'Executive/Senior VP' : '#e4deae',
                  'Shareholder (10%+)' : '#fff1bc',
                  'Other' : '#ededed'}

grouped_df = filtered_df.groupby(['Symbol', 'Relationship', 'Role'])['Amount'].sum()

top10_df = grouped_df[grouped_df.index.get_level_values(0).isin(top_10.index)]

reset_top10df = top10_df.reset_index().sort_values(by='Amount', ascending=False)

fig_top10_roles = px.bar(
    reset_top10df,
    x='Symbol',
    y='Amount',
    color='Role',
    category_orders={'Symbol': top_10.index,
                     'Role' : ['CEO', 'CFO', 'Other C-level', 'Director', 'President', 'Executive/Senior VP', 'Shareholder (10%+)', 'Other']},
    color_discrete_map=role_color_map,
)

fig_top10_roles.update_layout(legend=dict(
    yanchor="top",
    y=0.99,
    xanchor="right",
    x=0.99
))


st.plotly_chart(fig_top10_roles, use_container_width=True)

# Dataframe with detailed transactions

st.markdown("### Detailed transactions")
st.dataframe(filtered_df)

# Number of insiders and insider breakdown

symbol_list = filtered_df['Symbol'].unique()

n_insiders_data = []

for s in symbol_list:
    n_insiders = filtered_df[filtered_df['Symbol'] == s]['Insider name'].nunique()
    investment = filtered_df[filtered_df['Symbol'] == s]['Amount'].sum()
    n_insiders_data.append({'Ticker symbol': s, 'Number of insiders': n_insiders, 'Total purchases':investment})

n_insiders_df = pd.DataFrame(n_insiders_data).set_index('Ticker symbol')

n_insiders_df_plot = n_insiders_df.nlargest(20, 'Number of insiders').sort_values(by='Number of insiders', ascending=False)

filtered_data = filtered_df[filtered_df['Symbol'].isin(n_insiders_df_plot.index)]

insider_breakdown_data = filtered_data.groupby(['Symbol', 'Insider name', 'Relationship', 'Role'])['Amount'].sum().to_frame()
insider_breakdown_data['Number of insiders'] = 1

insider_breakdown_chart = insider_breakdown_data.groupby(['Symbol', 'Relationship', 'Role'])['Number of insiders'].sum().to_frame().reset_index()

insider_breakdown_fig = px.bar(
    insider_breakdown_chart,
    x='Symbol',
    y='Number of insiders',
    color='Role',
    title="Title of the chart",
    template="plotly_white",
    category_orders={'Symbol': insider_breakdown_chart.groupby('Symbol')['Number of insiders'].sum().sort_values(ascending=False).index,
                     'Role' : ['CEO', 'CFO', 'Other C-level', 'Director', 'President', 'Executive/Senior VP', 'Shareholder (10%+)', 'Other']},
    color_discrete_map=role_color_map,
)

insider_breakdown_fig.update_layout(
    legend=dict(
        yanchor="top",
        y=1.05,  # Adjust the y position of the legend
        xanchor="right",
        x=0.99
    ),
    margin=dict(b=50, t=50, l=10, r=10),  # Adjust the bottom margin to make space for the legend
)

st.plotly_chart(insider_breakdown_fig, use_container_width=True)

st.dataframe(n_insiders_df.sort_values(by='Number of insiders', ascending=False))