import streamlit as st
import pandas as pd
import altair as alt

st.title("KnockOut-Investitions Simulation auf Indizes", anchor="title")

top = st.container(border=True)
bottom = st.container(border=True)


with bottom:
    
    st.subheader("Aktuelle Regler")

    hebel = st.radio(
        "Hebel",
        ["3", "5", "10"]
    )
    hebel = float(hebel)

    selected_index = st.radio(
        "Wähle einen Index aus:",
        ["DAX", "S&P 500", "FSTE China 50"]
    )


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
    df_all_index["index_growth_with_hebel"] = df_all_index["index_growth"] * hebel
    df_all_index["index_investpoint"] = df_all_index["index_growth"] <= -0.05
 

    df_all_index['current_invest_wert'] = 0.0
    knockout_count = 0

    aktive_investment = 0.0
    is_invested = False        

    for i in df_all_index.index:
        if df_all_index.loc[i, "index_investpoint"] and not is_invested:
            active_investment = df_all_index.loc[i, "index_wert"]
            is_invested = True
            df_all_index.loc[i, "current_invest_wert"] = active_investment
            continue

        if is_invested:
            active_investment += df_all_index.loc[i, "index_growth_with_hebel"]
            
            if active_investment <= df_all_index.loc[i, "knockout"] and is_invested:
                knockout_count += 1
                active_investment = 0.0
                is_invested = False
            
            
            df_all_index.loc[i, "current_invest_wert"] = active_investment



    # df_all_index.to_csv("TestIndexRND_filtered.csv", index=False) #Speichern der CSV
    # st.write(df_all_index)


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
        y="knockout:Q"
    )

    line_invest = chart.mark_line(color="yellow").encode(
        x="zeit:T",
        y="current_invest_wert:Q"
    )

    st.altair_chart(
        (line_index + line_knockout + line_invest),
        use_container_width=True
    )


    st.subheader("Aktuelle Kennzahlen")
    

    col1, col2, col3, col4 = st.columns(4)

    with col1: 
        # Aktueller Kurs
        current_index_wert = df_all_index.groupby("index_name")["index_wert"].last().round(3)
        current_index_wert = float(current_index_wert[selected_index])
        st.metric("Kurs", (current_index_wert), "Test")

    with col2:
        # Aktuelle KnockOut Grenze
        current_knockout = df_all_index["knockout"].iloc[-1]
        current_knockout = float(round(current_knockout, 3))    
        st.metric("KnockOut", current_knockout, "Test" )

    with col3:
        # Buy In
        first_index_wert = df_all_index.groupby("index_name")["index_wert"].first().round(3)
        first_index_wert = float(first_index_wert[selected_index])
        st.metric("Buy In", (first_index_wert), "Test")

    with col4:
        st.metric("Knockouts", knockout_count, "Test")
  
