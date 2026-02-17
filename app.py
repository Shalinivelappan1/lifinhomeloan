import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")
st.title("🏠 Buy vs Rent — Advanced Classroom Simulator")

# =========================================================
# SIDEBAR INPUTS
# =========================================================

st.sidebar.header("Property")
price = st.sidebar.number_input("House price (₹)", value=8000000)
down_pct = st.sidebar.slider("Down payment %", 0.1, 0.5, 0.2)
loan_rate = st.sidebar.number_input("Loan interest %", value=8.5)
tenure = st.sidebar.number_input("Loan tenure (years)", value=20)

st.sidebar.header("Rent")
rent0 = st.sidebar.number_input("Monthly rent", value=25000)
rent_growth = st.sidebar.number_input("Rent growth %", value=5)

st.sidebar.header("Market")
house_growth = st.sidebar.number_input("House growth %", value=5)
inv_return = st.sidebar.number_input("Investment return %", value=10)
inflation = st.sidebar.number_input("Inflation %", value=5)
disc = st.sidebar.number_input("Discount rate %", value=8)

st.sidebar.header("Exit")
exit_year = st.sidebar.slider("Sell after years", 3, 25, 10)

st.sidebar.header("Costs")
buy_commission = st.sidebar.number_input("Buy commission %", value=1.0)
sell_commission = st.sidebar.number_input("Sell commission %", value=1.0)
maintenance_pct = st.sidebar.number_input("Maintenance %", value=1.0)

st.sidebar.header("Tax (India)")
tax_rate = st.sidebar.number_input("Income tax rate %", value=30.0)
interest_deduction = st.sidebar.number_input("Interest deduction limit", value=200000)
principal_deduction = st.sidebar.number_input("Principal deduction limit", value=150000)

# =========================================================
# EMI
# =========================================================

loan_amt = price*(1-down_pct)
r = loan_rate/100/12
n = tenure*12
emi = loan_amt*r*(1+r)**n/((1+r)**n-1)

st.metric("Monthly EMI", f"₹{emi:,.0f}")

# =========================================================
# AMORTIZATION + EQUITY BUILDUP
# =========================================================

balance = loan_amt
schedule = []

for m in range(1, exit_year*12+1):
    interest = balance*r
    principal = emi - interest
    balance -= principal
    equity = price - balance

    schedule.append([m/12, interest, principal, balance, equity])

sched = pd.DataFrame(schedule,
    columns=["Year","Interest","Principal","Balance","Equity"])

# =========================================================
# TAX BENEFIT
# =========================================================

def tax_saving(interest, principal):
    interest_claim = min(interest, interest_deduction)
    principal_claim = min(principal, principal_deduction)
    return (interest_claim + principal_claim)*tax_rate/100

# =========================================================
# CASHFLOW GENERATOR
# =========================================================

def compute_npv(hg, rg):

    downpayment = price*down_pct
    buy_comm = price*buy_commission/100

    cf_buy = [-downpayment - buy_comm]
    cf_rent = []

    balance = loan_amt

    for y in range(1, exit_year+1):

        # RENT
        rent = rent0*(1+rg/100)**y
        cf_rent.append(-(rent*12))

        # BUY
        interest_year = sched[sched["Year"].between(y-1,y)]["Interest"].sum()
        principal_year = sched[sched["Year"].between(y-1,y)]["Principal"].sum()

        tax = tax_saving(interest_year, principal_year)

        maintenance = price*(maintenance_pct/100)
        cf_buy.append(-(emi*12 + maintenance) + tax)

    # resale
    future_price = price*(1+hg/100)**exit_year
    resale = future_price*(1-sell_commission/100)
    cf_buy[-1] += resale

    # investment if renting
    invest = downpayment*(1+inv_return/100)**exit_year
    cf_rent[-1] += invest

    def npv(rate, cfs):
        return sum(cf/((1+rate/100)**i) for i, cf in enumerate(cfs))

    # inflation adjusted
    real_disc = ((1+disc/100)/(1+inflation/100)-1)*100

    return npv(real_disc, cf_buy), npv(real_disc, cf_rent)

# =========================================================
# SCENARIOS
# =========================================================

scenarios = {
    "Base": (house_growth, rent_growth),
    "Boom": (house_growth+3, rent_growth+2),
    "Crash": (house_growth-3, rent_growth-1)
}

rows = []
for name,(hg,rg) in scenarios.items():
    b,r = compute_npv(hg,rg)
    rows.append([name, b, r, b-r])

df_scen = pd.DataFrame(rows,
    columns=["Scenario","NPV Buy","NPV Rent","Buy-Rent"])

st.subheader("Scenario comparison")
st.dataframe(df_scen)

# =========================================================
# SLIDER GRAPH
# =========================================================

st.subheader("Interactive growth slider")

g = st.slider("House growth sensitivity", -5, 15, house_growth)

b,r = compute_npv(g, rent_growth)

st.write("NPV Buy:", f"₹{b:,.0f}")
st.write("NPV Rent:", f"₹{r:,.0f}")

# =========================================================
# EQUITY BUILDUP CHART
# =========================================================

st.subheader("Equity buildup")

fig = plt.figure()
plt.plot(sched["Year"], sched["Equity"])
plt.xlabel("Year")
plt.ylabel("Equity")
st.pyplot(fig)

# =========================================================
# NPV VS HOLDING PERIOD GRAPH
# =========================================================

st.subheader("NPV vs holding period")

years = range(3,26)
buy_vals = []
rent_vals = []

for y in years:
    exit_year = y
    b,r = compute_npv(house_growth, rent_growth)
    buy_vals.append(b)
    rent_vals.append(r)

fig2 = plt.figure()
plt.plot(years, buy_vals, label="Buy")
plt.plot(years, rent_vals, label="Rent")
plt.legend()
plt.xlabel("Years")
plt.ylabel("NPV")
st.pyplot(fig2)
