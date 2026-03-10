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

    df_all_index = pd.read_csv("TestIndexRND.csv")

    df_all_index["zeit"] = pd.to_datetime(
        df_all_index["zeit"],
        format="%y-%m-%d"
    )

    df_all_index = df_all_index[
    df_all_index["index_name"] == selected_index
    ].reset_index(drop=True)

    df_all_index["index_growth"] = df_all_index["index_wert"].pct_change().fillna(0)
    df_all_index["index_investpoint"] = df_all_index["index_growth"] <= -0.05
       

    df_all_index["calculated_hebel"] = 0.0
    df_all_index["calculated_knockout_barrier"] = 0.0

    df_all_index['current_invest_wert'] = 0.0
    knockout_count = 0

    active_investment = 0.0
    is_invested = False  


    df_all_index["calculated_hebel"] = selected_hebel #gilt solange nicht investiert ist bzw. Startpunkt ist immer = selected_hebel

    for i in range (1, len(df_all_index)):

        df_all_index.loc[i, "calculated_knockout_barrier"] = df_all_index.loc[i, "index_wert"] * (1 - 1 / df_all_index.loc[i-1, "calculated_hebel"]) * (1 + 0.04/365)

        if df_all_index.loc[i, "index_investpoint"] and not is_invested and remaining_budget > 0:
            is_invested = True
            active_investment = df_all_index.loc[i, "index_wert"]   
            remaining_budget = remaining_budget * 0.8
            df_all_index.loc[i, "current_invest_wert"] = active_investment
            continue

        if is_invested:

            df_all_index.loc[i, "calculated_hebel"] = df_all_index.loc[i, "index_wert"] / (df_all_index.loc[i, "index_wert"] - df_all_index.loc[i, "calculated_knockout_barrier"])

            df_all_index["index_growth_with_hebel"] = (
                df_all_index["index_growth"] * df_all_index["calculated_hebel"]
                )
            active_investment += df_all_index.loc[i, "index_growth_with_hebel"]

            if active_investment <= df_all_index.loc[i, "calculated_knockout_barrier"] and is_invested:
                knockout_count += 1
                active_investment = 0.0
                is_invested = False

            df_all_index.loc[i, "current_invest_wert"] = active_investment



    # df_all_index.to_csv("TestIndexRND_filtered.csv", index=False) #Speichern der CSV
    st.write(df_all_index)


    chart = alt.Chart(df_all_index)

    line_index = chart.mark_line(color="aqua").encode(
       x=alt.X(
        "zeit:T",
        title="Zeit",
        axis=alt.Axis(
            format="%d %b"
            )
        ),
        y=alt.Y("index_wert:Q", title="Kurs")
    )

    line_knockout = chart.mark_line(color="red").encode(
        x="zeit:T",
        y="calculated_knockout_barrier:Q"
    )

    line_invest = chart.mark_line(color="yellow").encode(
        x="zeit:T",
        y="current_invest_wert:Q"
    )


    st.altair_chart(
        (line_index + line_knockout + line_invest),
        use_container_width=True
    )


  

with mid:

    st.subheader("Aktuelle Kennzahlen")
    

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1: 
        # Aktueller Kurs
        current_index_wert = df_all_index.groupby("index_name")["index_wert"].last().round(3)
        current_index_wert = float(current_index_wert[selected_index])
        st.metric("Kurs", (current_index_wert), "Test")

    with col2:
        # Aktuelle KnockOut Grenze
        current_knockout = df_all_index["calculated_knockout_barrier"].iloc[-1]
        current_knockout = float(round(current_knockout, 3))    
        st.metric("KnockOut", current_knockout, "Test" )

    with col3:
        # Buy In
        first_index_wert = df_all_index.groupby("index_name")["index_wert"].first().round(3)
        first_index_wert = float(first_index_wert[selected_index])
        st.metric("Buy In", (first_index_wert), "Test")

    with col4:
        st.metric("Knockouts", knockout_count, "Test")

    with col5:
        st.metric("Remaining Budget", remaining_budget, "Test")
        