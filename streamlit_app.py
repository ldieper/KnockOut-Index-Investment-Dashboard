import streamlit as st
import pandas as pd
import altair as alt
from investment import investment

st.set_page_config(layout="wide")

st.title("KnockOut-Investition auf Indizes")

top = st.container(border=True)
mid = st.container(border=True)
bottom = st.container(border=True)


with bottom:
    
    st.subheader("Aktuelle Regler")

    col1, col2, col3 = st.columns(3)

    with col1:
        selected_index = st.radio(
            "Index",
            ["DAX", "S&P 500", "FSTE China 50"]
        )

        selecte_timeframe = st.radio(
            "Timeframe",
            ["Seit Beginn", "5 Jahre", "Aktive Investments"]
        )

    with col2:  
        selected_hebel = st.radio(
            "Hebel",
            ["3", "5", "10"]
        )
        selected_hebel = float(selected_hebel)

    with col3:
        selected_budget = st.radio(
            "Budget",
            ["5000", "10000"]     
        )
        selected_budget = float(selected_budget)
        remaining_budget = selected_budget
        

with top:
    st.subheader(f"Kursverlauf - {selected_index}")

    index_map = {
        "DAX": "yfinance_indizes/^GDAXI.json",
        "S&P 500": "yfinance_indizes/^GSPC.json",
        "FSTE China 50": "yfinance_indizes/^HSI.json"
    }

    selected_file = index_map[selected_index]
    df_yf = pd.read_json(selected_file, orient="index")

    df_yf.index = pd.to_datetime(df_yf.index)
    
    df_yf.columns = ["index_wert"]
    df_yf.index.name = "date"

    df_all_index = df_yf.reset_index()


    df_all_index["index_growth"] = df_all_index["index_wert"].pct_change().fillna(0)
    df_all_index = df_all_index.set_index("date")

    
    df_all_index = df_all_index.reset_index()

    df_all_index["calculated_hebel"] = None
    df_all_index["calculated_knockout_barrier"] = None

    df_all_index["index_investpoint"] = None
    df_all_index['current_invest_wert'] = None



    df_all_index["yearly_high"] = (
        df_all_index["index_wert"]
            .rolling(window=252, min_periods=1)  # ~trading days in a year
            .max()
    )#im Zeitfenster (rolling) der letzten 52-Wochen

    start_date = df_all_index["date"].iloc[0] + pd.DateOffset(years=1) #1jahr nach anfang von Index
    mask = df_all_index["date"] > start_date #mask = für Investments relevanter bereich


    investment_break = 20 #Pause bis zum nächsten Investment, Ausnahme: 20% Drop

    for i in df_all_index[mask].index: #Bereich, der für Investments relevant ist
        price = df_all_index.loc[i, "index_wert"]
        high = df_all_index.loc[i, "yearly_high"]

        if price < high * 0.9:
            if not df_all_index["index_investpoint"].iloc[max(0, i-investment_break):i].any():  # Kein Investment im letzten Monat (20 Handelstage)
                df_all_index.loc[i, "index_investpoint"] = True

        if price < high * 0.8:
             if df_all_index["index_investpoint"].iloc[max(0, i-investment_break):i].sum() < 2 and 0 < df_all_index["index_investpoint"].iloc[max(0, i-investment_break):i].sum():  # Investment im letzten Monat (20 Handelstage)
                df_all_index.loc[i, "index_investpoint"] = True
    
    rows = [] #Zum unterscheiden der Reihen, der Investments
    investments = [] #Liste der Klassen von Investment
    investment_count = 0 #Zählt die Anzahl an Investment und wird für die Vergabe der inv.id verwendet

    for i in df_all_index[mask].index:

        if df_all_index.loc[i, "index_investpoint"]:
            
            investment_count += 1
            new_inv = investment(source=df_all_index, #Erstellen eines neuen Investments
                         i=i,
                         selected_hebel=selected_hebel,
                         selected_budget=selected_budget,
                         remaining_budget=remaining_budget,
                         inv_id=investment_count) #ID des Investments == Invest_counter
            investments.append(new_inv) #Hinzufügen zu investments Liste
            new_inv.start_investment() #Startet das Investment
            remaining_budget -= new_inv.active_investment #Abziehen des Investments vom Budget

        for inv in investments:

            if not inv.active: #Falls das Investment bereits inaktiv ist zu diesem Zeitpunkt
                continue

            inv.update_current_knockout_barrier(i) #Aktualisiert die Knockoutbarriere
            inv.update_investment_value(i) #Aktualisiert den aktuellen Wert des Investments

            #Fall eines Knockouts, berechnet aus Hebel
            if  inv.get_hebel(i=i) == 0:
                inv.reset_investment(type="knockout")
                continue

            #Fall eines Knockouts, berechnet aus aktuellem Wert des Investments
            if inv.active_investment <= 0:
                inv.reset_investment(type="knockout")
                continue

            #Fall eines regulären Verkaufs, weil der Hebel unter 1.5x gefallen ist
            if inv.get_hebel(i=i) <= 1.5:
                inv.reset_investment(type="sell")
                continue

            # speichern der Werte in zuordbaren Reihen
            rows.append({
                "date": df_all_index.loc[i, "date"],
                "inv_id": inv.id,
                "knockout_barrier": inv.get_current_knockout_barrier(),
                "current_value": inv.active_investment,
                "hebel": inv.get_hebel(i=i),
                "rendite": inv.get_rendite(i=i)
            })







    #trades_count = len(investment) #Anzahl an trades
    #active_trades  = sum(1 for inv in investment if inv.active)
    #closed_trades = sum(1 for inv in investment if not inv.active)
    #sells_count = sum(1 for inv in investment if inv.closing_reason) #True = Sell
    #knockouts_count = sum(1 for inv in investment if not inv.closing_reason) #False = Knockout


df_investment = pd.DataFrame(rows) #Dataframe aus den gesammelten Reihen der Investments
df_all_index["date"] = pd.to_datetime(df_all_index["date"])
df_investment["date"] = pd.to_datetime(df_investment["date"])

df_plot = pd.merge(
    df_all_index,
    df_investment[["date", "current_value", "inv_id", "knockout_barrier", "hebel", "rendite"]],
    on="date",
    how="left"
)

base = alt.Chart(df_plot).encode(
    x=alt.X("date:T", title="Datum", axis=alt.Axis(format="%d %b %y"))
)


left_axis_group = alt.layer(
    base.mark_line(color="#BA2BAC").encode(
        y=alt.Y("index_wert:Q", title="Index & Barrier Level")
    ),
    base.mark_line(color="#c4265e", strokeDash=[4, 2]).encode(
        y="knockout_barrier:Q",
        detail="inv_id:N" 
    )
)

right_axis_group = alt.Chart(df_investment).mark_line(color="#e2e22e", size=2).encode(
    x="date:T",
    y=alt.Y("current_value:Q", title="Investment Value (€)"),
    color="inv_id:N"
)

combined_chart = alt.layer(
    left_axis_group,
    right_axis_group
).resolve_scale(
    y="independent"
)

st.altair_chart(combined_chart, use_container_width=True)           


with mid:

    st.subheader("Aktuelle Kennzahlen")
    

    col1, col2, col3 = st.columns(3)

    with col1:
        current_index_wert = float(df_all_index["index_wert"].iloc[-1])
        st.metric("Kurs", round(current_index_wert, 3), "Aktuell")

        st.metric("Remaining Budget", round(remaining_budget, 2), "Test")

    with col2:
        if df_all_index["calculated_knockout_barrier"].iloc[-1] is not None:
            current_knockout = df_all_index["calculated_knockout_barrier"].iloc[-1]
            current_knockout = float(round(current_knockout, 3))  
        else:  
            current_knockout = 0.0
        st.metric("KnockOut", current_knockout, "Test" )

        #st.metric("Knockouts", state["knockout_count"], "Test")

    #with col3:
        #st.metric("Rendite", state["rendite"], "Test")

        #st.metric("Sells", sells_count, "Test")

        #st.metric("Trades", trades_count, "Test")