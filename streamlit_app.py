import streamlit as st
import pandas as pd
import altair as alt
from investment_simulation import run_simulation

st.set_page_config(layout="wide")

st.title("KnockOut-Investition auf Indizes")

top = st.container(border=True)
bottom = st.container(border=True)


if "selected_index" not in st.session_state:
    st.session_state.selected_index = "DAX"

if "selected_hebel" not in st.session_state:
    st.session_state.selected_hebel = 3.0



with top:
    st.subheader(f"Kursverlauf - {st.session_state.selected_index}")

    index_map = {
        "DAX": "yfinance_indizes/^GDAXI.json",
        "S&P 500": "yfinance_indizes/^GSPC.json",
        "FSTE China 50": "yfinance_indizes/^HSI.json"
    }

    selected_file = index_map[st.session_state.selected_index]
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

        if df_all_index["index_investpoint"].sum() == 0:
            if price < high * 0.9: #Erster Investmentpunkt, wenn Kurs unter 90% des 52-Wochen-Hochs fällt
                df_all_index.loc[i, "index_investpoint"] = True
                last_investment_point_value = df_all_index.loc[i, "index_wert"]
                continue

        if price < high * 0.9:
            #if investment_break_type == "20 Tage":
                if not df_all_index["index_investpoint"].iloc[max(0, i-20):i].any():  
                    df_all_index.loc[i, "index_investpoint"] = True
                    last_investment_point_value = df_all_index.loc[i, "index_wert"]
                    continue

            #elif investment_break_type == "Bis Wiederanstieg auf gleichen Wert" and df_all_index.loc[i, "index_wert"] > last_investment_point_value: 
            #    df_all_index.loc[i, "index_investpoint"] = True
            #    last_investment_point_value = df_all_index.loc[i, "index_wert"]
            #    continue


    #Sim-Run
    investments_list, remaining_budget, df_investment = run_simulation(
        df_all_index,
        mask,
        st.session_state.selected_hebel,
        selected_budget,
        remaining_budget
    )
    
    
    
    #discarded_count = sum(1 for inv in investments_list if inv.closing_reason == 2) #Summe der fehlerhaften Investments, bei denen nicht genug Geld für den Kauf einer Option vorhanden war
    #trades_count = sum(1 for inv in investments_list if not inv.closing_reason == 2) #Anzahl an trades (ohne fehlerhafte, ohne genug Geld)
    #active_trades  = sum(1 for inv in investments_list if inv.active)
    #closed_trades = sum(1 for inv in investments_list if not inv.active)
    #sells_count = sum(1 for inv in investments_list if inv.closing_reason == 1) #True = Sell
    #knockouts_count = sum(1 for inv in investments_list if inv.closing_reason == 0) #False = Knockout
    #not_enough_money_count = sum(1 for inv in investments_list if inv.closing_reason == 2) #Not enough money

    #loss_sum = sum(inv.starting_investment for inv in investments_list if inv.closing_reason == 0) #Summe der Verluste durch Knockout
    #profit_sum = sum(inv.get_gewinn() for inv in investments_list if inv.closing_reason != 2) #Summe der Gewinne durch regulären Verkauf
    #final_gewinn = round(profit_sum - loss_sum, 2)
    #total_invested_sum = sum(inv.starting_investment for inv in investments_list if inv.closing_reason != 2) #Summe des investierten Kapitals (ohne fehlerhafte Investments)
    #total_rendite = round(final_gewinn / total_invested_sum * 100, 2) if total_invested_sum > 0 else 0 #Rendite in Prozent

    discarded_count = (df_investment["closing_reason"] == 2).sum() #
    
    closed_trades = (~df_investment["active"]).sum() #
    sells_count = (df_investment["closing_reason"] == 1).sum() #
    knockouts_count = (df_investment["closing_reason"] == 0).sum() #
    not_enough_money_count = (df_investment["closing_reason"] == 2).sum() #
    cumulative_value = df_investment["cumulative_investment_value"].iloc[-1] #


    final_trades = df_investment.groupby("inv_id").last()
    valid_trades = final_trades[final_trades["closing_reason"] != 2]

    final_gewinn = round(valid_trades["gewinn"].sum(), 2)
    trades_count = (valid_trades["closing_reason"] != 2).sum() #
    active_trades = (valid_trades["active"] == True).sum() #
    loss_sum = round(valid_trades.loc[valid_trades["closing_reason"] == 0, "starting_investment"].sum(), 2)


    print(final_gewinn)

    total_invested_sum = df_investment.loc[df_investment["closing_reason"] != 2,"starting_investment"].sum()

    total_rendite = round(final_gewinn / total_invested_sum * 100, 2) if total_invested_sum > 0 else 0


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


with bottom:

    bottom_left, bottom_right = st.columns([0.7, 0.3])

    with bottom_left:
        with st.container(border=True):

            st.subheader("Aktuelle Kennzahlen")
            

            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:
                st.metric("Investment-Kurs", f"€ {round(cumulative_value, 2):,.2f}".replace(",", " "), "Test")
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

    with bottom_right:
        with st.container(border=True):

            st.subheader("Einstellungen")

            col1, col2 = st.columns(2)

            with col1:
                st.radio(
                    "Index",
                    ["DAX", "S&P 500", "FSTE China 50"],
                    key="selected_index"
                )

            with col2:
                st.radio(
                    "Hebel",
                    [3, 5, 10],
                    key="selected_hebel"
                )

            #with col3:  
            #   st.metric
            #    investment_break_type = st.radio(
            #        "Wähle die Dauer der Investitionsperiode",
            #       ["20 Tage", "Bis Wiederanstieg auf gleichen Wert"]
            #    )