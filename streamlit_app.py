import streamlit as st
import pandas as pd
import altair as alt
import custom_funcs_investment as cfi

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
            ["500", "1000"]     
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
    df_yf.index.name = "zeit"

    df_all_index = df_yf.reset_index()


    df_all_index["index_growth"] = df_all_index["index_wert"].pct_change().fillna(0)

    df_all_index["calculated_hebel"] = None
    df_all_index["calculated_knockout_barrier"] = None

    df_all_index['current_invest_wert'] = None

    state = {
        "knockout_count": 0,
        "sells_count": 0,
        "trades_count": 0,
        "rendite": 0.0,
        "index_investpoint_wert": 0.0,
        "active_investment": 0.0,
        "is_invested": False,
        "first_investment_date": df_all_index["zeit"].iloc[0],
        "last_investment_date": df_all_index["zeit"].iloc[0],
        "fault_not_enough_budget": False,
        "bezugsverhältnis": 0.01
    }


    for i in range (1, len(df_all_index)):

        df_all_index.loc[i,"index_investpoint"] = df_all_index.loc[i, "index_growth"] + df_all_index.loc[i-1, "index_growth"] <= -0.05

        if state["is_invested"] and not state["fault_not_enough_budget"]:
            df_all_index.loc[i, "calculated_knockout_barrier"] = cfi.get_knockout_barrier(df_all_index, i)

            if  cfi.get_hebel(df_all_index, i) == 0: #df_all_index.loc[i, "index_wert"] <= df_all_index.loc[i, "calculated_knockout_barrier"]
                cfi.knockout(df_all_index, state,i)
                continue

            df_all_index.loc[i, "calculated_hebel"] = cfi.get_hebel(df_all_index, i)
            state["active_investment"] = cfi.get_active_investment(df_all_index, i, state)

            if state["active_investment"] <= 0:
                cfi.knockout(df_all_index, state, i)
                state["last_investment_date"] = df_all_index.loc[i, "zeit"]
                continue

            df_all_index.loc[i, "current_invest_wert"] = state["active_investment"]

            if df_all_index.loc[i, "calculated_hebel"] <= 1.5:
                state["rendite"] += cfi.get_rendite(state)
                cfi.reset_investment(df_all_index, state, i)
                state["last_investment_date"] = df_all_index.loc[i, "zeit"]
                continue

            state["last_investment_date"] = df_all_index.loc[i, "zeit"]

        elif df_all_index.loc[i, "index_investpoint"] and not state["is_invested"] and not state["fault_not_enough_budget"]:
            cfi.start_investment(df_all_index, state, i, selected_hebel, selected_budget, remaining_budget)

    first_investment_date = df_all_index.loc[df_all_index['index_investpoint'] == True, 'zeit'].iloc[0] #erste Investition (Datum)

    #barrier_series = df_all_index.loc[df_all_index['calculated_knockout_barrier'] == True, 'zeit'] #vorgefiltert für letzten Tradepunkt (Iloc gibt sonst Fehler aus)
    #last_investment_point = next(iter(barrier_series.tail(1)), df_all_index['zeit'].iloc[-1]) #,wenn Empty = LastDate, sonst letzter Tradepunkt

    base = alt.Chart(df_all_index).encode(
        x=alt.X("zeit:T", title="Datum", axis=alt.Axis(format="%d %b %y"))
    )

    line_index = base.mark_line(color="#BA2BAC").encode(
        y=alt.Y("index_wert:Q", title="Index Stand (Punkte)", scale=alt.Scale(zero=False))
    )

    line_knockout = base.mark_line(color="#c4265e").encode(
        y="calculated_knockout_barrier:Q"
    )

    line_invest = base.mark_line(color="#e2e22e", size=2).encode(
        y=alt.Y("current_invest_wert:Q", 
                title="Investment Wert (€)", 
                axis=alt.Axis(orient="right"))
    )

    if selecte_timeframe == "5 Jahre":
        view_start = df_all_index["zeit"].iloc[-1] - pd.DateOffset(years=5)
        view_end = df_all_index["zeit"].iloc[-1]
    elif selecte_timeframe == "Aktive Investments":
        view_start = first_investment_date
        view_end = state["last_investment_date"]
    else:
        view_start = df_all_index["zeit"].iloc[0]
        view_end = df_all_index["zeit"].iloc[-1]

    x_parallax = alt.selection_interval(bind='scales', encodings=['x'])

    combined_chart = alt.layer(
        line_index + line_knockout, 
        line_invest
    ).resolve_scale(
        y="independent" 
    ).encode(
         x=alt.X('x:T', 
                scale=alt.Scale(domain=[view_start, view_end]), #mögliche Beschränkung des x-Achsen Bereichs
        )
    ).add_params(
        x_parallax  
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

        st.metric("Knockouts", state["knockout_count"], "Test")

        st.metric("Interval", view_start.strftime("%d %b %Y") + "-" + view_end.strftime("%d %b %Y"), "Test")

    with col3:
        st.metric("Rendite", state["rendite"], "Test")

        st.metric("Sells", state["sells_count"], "Test")

        st.metric("Trades", state["trades_count"], "Test")
        