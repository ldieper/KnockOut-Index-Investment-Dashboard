import streamlit as st
import pandas as pd
import altair as alt
from investment import Investment

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

    with col2:  
        selected_hebel = st.radio(
            "Hebel",
            ["3", "5", "10"]
        )
        selected_hebel = float(selected_hebel)

    with col3:  
        investment_break = st.slider("Wähle die Anzahl der Handels-Tage, die zwischen zwei Investments liegen soll",
                        min_value=5,
                        max_value=252,
                        value=200,)
        investment_break = int(investment_break)
        

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


    selected_budget = 500
    remaining_budget = selected_budget



    df_all_index["yearly_high"] = (
        df_all_index["index_wert"]
            .rolling(window=252, min_periods=1)  # ~trading days in a year
            .max()
    )#im Zeitfenster (rolling) der letzten 52-Wochen

    start_date = df_all_index["date"].iloc[0] + pd.DateOffset(years=1) #1jahr nach anfang von Index
    mask = df_all_index["date"] > start_date #mask = für Investments relevanter bereich


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
    investments_list = [] #Liste der Klassen von Investment
    investment_count = 0 #Zählt die Anzahl an Investment und wird für die Vergabe der inv.id verwendet
    cumulative_investment_value = 0 #Kumulativer Wert aller Investments, um die Rendite und aktuelleb Stand zu berechnen

    def get_comulative_investment_value(i):
        total_value = 0
        for inv in investments_list:
            if inv.active:
                total_value += inv.get_investment_value()
        return total_value

    for i in df_all_index[mask].index:

        if i%20 == 0: #Alle 20 Handelstage (ca. 1 Monat umgerechnet) wird das monatliche Budget erhöht
            remaining_budget += selected_budget

        if df_all_index.loc[i, "index_investpoint"]:
            
            investment_count += 1
            new_inv = Investment(source=df_all_index, #Erstellen eines neuen Investments
                         i=i,
                         selected_hebel=selected_hebel,
                         selected_budget=selected_budget,
                         remaining_budget=remaining_budget,
                         inv_id=investment_count) #ID des Investments == Invest_counter
            investments_list.append(new_inv) #Hinzufügen zu investments Liste
            new_inv.start_investment() #Startet das Investment
            remaining_budget -= new_inv.get_investment_value() #Abziehen des Investments vom Budget

        for inv in investments_list:

            if not inv.active: #Falls das Investment bereits inaktiv ist zu diesem Zeitpunkt
                continue

            

            inv.update_current_knockout_barrier(i=i) #Aktualisiert die Knockoutbarriere
            inv.update_investment_value(i=i) #Aktualisiert den aktuellen Wert des Investments
            inv.update_hebel(i=i) #Aktualisiert den Hebel des Investments
            inv.update_gewinn() #Aktualisiert die Rendite des Investments

            #Fall eines Knockouts, berechnet aus Hebel
            if  inv.get_hebel() == 0:
                inv.reset_investment(type="knockout")
                continue

            #Fall eines Knockouts, berechnet aus aktuellem Wert des Investments
            if inv.get_investment_value() <= 0:
                inv.reset_investment(type="knockout")
                continue

            #Fall eines regulären Verkaufs, weil der Hebel unter 1.5x gefallen ist
            if inv.get_hebel() <= 1.5:
                inv.reset_investment(type="sell")
                continue

            # speichern der Werte in zuordbaren Reihen
            rows.append({
                "date": df_all_index.loc[i, "date"],
                "inv_id": inv.id,
                "knockout_barrier": inv.get_current_knockout_barrier(),
                "current_value": inv.get_investment_value(),
                "hebel": inv.get_hebel(),
                "gewinn": inv.get_gewinn(),
                "cumulative_investment_value": get_comulative_investment_value(i),
            })

    
    discarded_count = sum(1 for inv in investments_list if inv.closing_reason == 2) #Summe der fehlerhaften Investments, bei denen nicht genug Geld für den Kauf einer Option vorhanden war
    trades_count = sum(1 for inv in investments_list if not inv.closing_reason == 2) #Anzahl an trades (ohne fehlerhafte, ohne genug Geld)
    active_trades  = sum(1 for inv in investments_list if inv.active)
    closed_trades = sum(1 for inv in investments_list if not inv.active)
    sells_count = sum(1 for inv in investments_list if inv.closing_reason == 1) #True = Sell
    knockouts_count = sum(1 for inv in investments_list if inv.closing_reason == 0) #False = Knockout
    not_enough_money_count = sum(1 for inv in investments_list if inv.closing_reason == 2) #Not enough money
    loss_sum = sum(inv.starting_investment for inv in investments_list if inv.closing_reason == 0) #Summe der Verluste durch Knockout
    profit_sum = sum(inv.get_gewinn() for inv in investments_list if inv.closing_reason != 2) #Summe der Gewinne durch regulären Verkauf
    final_gewinn = round(profit_sum - loss_sum, 2)
    total_invested_sum = sum(inv.starting_investment for inv in investments_list if inv.closing_reason != 2) #Summe des investierten Kapitals (ohne fehlerhafte Investments)
    total_rendite = round(final_gewinn / total_invested_sum * 100, 2) if total_invested_sum > 0 else 0 #Rendite in Prozent

    df_investment = pd.DataFrame(rows) #Dataframe aus den gesammelten Reihen der Investments
    df_all_index["date"] = pd.to_datetime(df_all_index["date"])
    df_investment["date"] = pd.to_datetime(df_investment["date"])

    df_plot = pd.merge(
        df_all_index,
        df_investment[["date", "current_value", "inv_id", "knockout_barrier", "hebel", "gewinn", "cumulative_investment_value"]],
        on="date",
        how="left"
    )

    base = alt.Chart(df_plot).encode(
        x=alt.X("date:T", title="Datum", axis=alt.Axis(format="%d %b %y"))
    )

    left_axis_group = alt.layer(
        # 1. The Index Line
        base.mark_line(color="#BA2BAC").encode(
            y=alt.Y("index_wert:Q", title="Index & Barrier Level")
        ),

        base.mark_line(color="#c4265e").encode( #alt: strokeDash=[4, 2]
            y="knockout_barrier:Q",
            detail="inv_id:N"   
        ).transform_calculate(
            # absolute Distanz zur Knockoutbarriere, um die Top 3 pro Datum zu identifizieren
            abs_dist="abs(datum.index_wert - datum.knockout_barrier)"
        ).transform_window(
            # Rank für die Distanz zur Knockoutbarriere, um die Top 3 pro Datum zu identifizieren
            rank="rank(abs_dist)",
            sort=[alt.SortField("abs_dist", order="ascending")],
            groupby=["date"]  # die top 2 pro Datum berechnen
        ).transform_filter(
            # Nur die höchsten 2 Barrieren pro Datum anzeigen
            alt.datum.rank <= 2
        )
    )

    right_axis_group = alt.Chart(df_investment).mark_line(color="#e2e22e", size=2).encode(
        x="date:T",
        y=alt.Y("cumulative_investment_value:Q", title="Investment Value (€)"),
        #color="inv_id:N"
    )

    combined_chart = alt.layer(
        left_axis_group,
        right_axis_group
    ).resolve_scale(
        y="independent"
    )
    st.altair_chart(combined_chart, width="stretch")           


with mid:

    st.subheader("Aktuelle Kennzahlen")
    

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Investment-Kurs", f"€ {round(rows[-1]['cumulative_investment_value'], 2):,.2f}".replace(",", " "), "Test")
        current_index_wert = float(df_all_index["index_wert"].iloc[-1])
        st.metric("Index-Kurs", f"{current_index_wert:,.3f}".replace(",", " "), "Test")

    with col2:
        st.metric("Gewinn", f"€ {final_gewinn:,.2f}".replace(",", " "), "Test")
        st.metric("Verkäufe (Hebel < 1.5x)", f"{sells_count}", "Test")

    with col3:
        st.metric("Verluste", f"€ {round(loss_sum, 2):,.2f}".replace(",", " "), "Test")
        st.metric("KnockOut", f"{knockouts_count}", "Test" )

    with col4:
        st.metric("Rendite", f"{total_rendite} %", "Test")
        st.metric("Anzahl aktiver Investments", f"{active_trades}", "Test")
        #st.metric("Fehlerhafte Investments (kein Geld)", f"{not_enough_money_count}", "Test")

    with col5:
        st.metric("Verfügbares Budget", f"€ {remaining_budget:,.2f}".replace(",", " "), "Test")
        st.metric("Monatliches Budget", f"€ 500,00", "Test")