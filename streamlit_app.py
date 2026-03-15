import streamlit as st
import pandas as pd
import altair as alt

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
        selected_budget = st.radio(
            "Budget",
            ["500", "1000"]     
        )
        selected_budget = float(selected_budget)
        remaining_budget = selected_budget
        

with top:
    st.subheader(f"Kursverlauf - {selected_index}")

with top:
    st.subheader(f"Kursverlauf - {selected_index}")

    df_yf_DAX = pd.read_json("yfinance_indizes/^GDAXI.json", orient="index")
    df_yf_GSPC = pd.read_json("yfinance_indizes/^GSPC.json", orient="index")
    df_yf_XINO = pd.read_json("yfinance_indizes/XINO.FGI.json", orient="index")


    if selected_index == "DAX" :
        df_yf = df_yf_DAX
    
    if selected_index == "S&P 500" :
        df_yf = df_yf_GSPC

    if selected_index == "FSTE China 50" :
        df_yf = df_yf_XINO

    df_yf.index = pd.to_datetime(df_yf.index)
    
    df_yf.columns = ["index_wert"]
    df_yf.index.name = "zeit"
    

    df_all_index = df_yf.reset_index()




    df_all_index["index_growth"] = df_all_index["index_wert"].pct_change().fillna(0)
    df_all_index["index_investpoint"] = df_all_index["index_growth"] <= -0.03 # noch zu ändernn!! 
       

    df_all_index["calculated_hebel"] = None
    df_all_index["calculated_knockout_barrier"] = None

    df_all_index['current_invest_wert'] = None
    knockout_count = 0

    rendite = None
    index_investpoint_wert = 0.0
    active_investment = 0.0
    is_invested = False  


    df_all_index["calculated_hebel"] = selected_hebel #gilt solange nicht investiert ist bzw. Startpunkt ist immer = selected_hebel

    for i in range (1, len(df_all_index)):

        if is_invested:
            prev_knockout_barrier = df_all_index.loc[i-1, "calculated_knockout_barrier"]

            
            knockout_daily_increase = (prev_knockout_barrier * 5) / 36000
            df_all_index.loc[i, "calculated_knockout_barrier"] = round(prev_knockout_barrier + knockout_daily_increase, 3)


            if df_all_index.loc[i, "index_wert"] <= df_all_index.loc[i, "calculated_knockout_barrier"]:
                df_all_index.loc[i, "current_invest_wert"] = 0.0
                df_all_index.loc[i, "calculated_hebel"] = 0
                active_investment = 0.0
                is_invested = False
                knockout_count += 1
                continue

            abstand = df_all_index.loc[i, "index_wert"] - df_all_index.loc[i, "calculated_knockout_barrier"]
            if abstand > 0:
                df_all_index.loc[i, "calculated_hebel"] = df_all_index.loc[i, "index_wert"] / abstand
            else:   
                df_all_index.loc[i, "calculated_hebel"] = 0

            current_growth = 1 + (df_all_index.loc[i, "index_growth"] * df_all_index.loc[i, "calculated_hebel"])
            active_investment = max(0.0, active_investment * current_growth)
            df_all_index.loc[i, "current_invest_wert"] = active_investment


            if df_all_index.loc[i, "calculated_hebel"] <= 1.5:
                rendite = round(active_investment - index_investpoint_wert, 3)
                is_invested = False

        if df_all_index.loc[i, "index_investpoint"] and not is_invested and remaining_budget > 0:
            is_invested = True
            df_all_index.loc[i, "calculated_knockout_barrier"] = df_all_index.loc[i, "index_wert"] * (1 - 1 / selected_hebel)
            remaining_budget = remaining_budget * 0.8
            active_investment = df_all_index.loc[i, "index_wert"]  
            df_all_index.loc[i, "current_invest_wert"] = active_investment
            index_investpoint_wert = df_all_index.loc[i, "index_wert"]



    # df_all_index.to_csv("TestIndexRND_filtered.csv", index=False) #Speichern der CSV
    st.write(df_all_index)


    chart = alt.Chart(df_all_index)

    line_index = chart.mark_line(color="#BA2BAC").encode(
       x=alt.X(
        "zeit:T",
        title="Zeit",
        axis=alt.Axis(
            format="%d %b"
            )
        ),
        y=alt.Y("index_wert:Q", title="Kurs")
    )

    line_knockout = chart.mark_line(color="#c4265e").encode(
        x="zeit:T",
        y="calculated_knockout_barrier:Q"
    )

    line_invest = chart.mark_line(color="#e2e22e").encode(
        x="zeit:T",
        y="current_invest_wert:Q"
    )


    st.altair_chart(
        (line_index + line_knockout + line_invest),
        use_container_width=True
    )


with mid:

    st.subheader("Aktuelle Kennzahlen")
    

    col1, col2, col3 = st.columns(3)

    with col1:
        current_index_wert = df_all_index.groupby("index_name")["index_wert"].last().round(3)
        current_index_wert = float(current_index_wert[selected_index])
        st.metric("Kurs", (current_index_wert), "Test")

        st.metric("Remaining Budget", remaining_budget, "Test")

    with col2:
        current_knockout = df_all_index["calculated_knockout_barrier"].iloc[-1]
        current_knockout = float(round(current_knockout, 3))    
        st.metric("KnockOut", current_knockout, "Test" )

        st.metric("Knockouts", knockout_count, "Test")

    with col3:
        st.metric("Rendite", rendite, "Test")
        