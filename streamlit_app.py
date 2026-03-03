import streamlit as st
import pandas as pd
import numpy as np
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

    selected_index = st.radio(
        "Wähle einen Index aus:",
        ["DAX", "S&P 500", "FSTE China 50"]
    )


with top:
    st.subheader(f"Kursverlauf - {selected_index}")

    df_all_index = pd.read_csv(
        "TestIndexRND.csv",
        parse_dates=["zeit"], # Spalte ist ein Datum
        dayfirst=True # Tag kommt zuerst. WICHTIG: Yfinance benutzt
    )

    # Von Roh zu ausgewähltem Index
    # st.write("Rohdaten")
    # st.dataframe(df_all_index)

    df_selected_index = df_all_index[
        df_all_index["index_name"] == selected_index]
    
    # Ausgabe gefilterter Indizes
    # st.write("Daten von Ausgewähltem Index:")
    # st.dataframe(df_selected_index) 

    chart = alt.Chart(df_selected_index)

    line_index = chart.mark_line().encode(
       x=alt.X(
        "zeit:T",
        title="Zeit",
        axis=alt.Axis(
            format="%d %b" # Tag/Monat als Format
            )
        ),
        y=alt.Y("index_wert:Q", title="Kurs")
    )

    line_knockout = chart.mark_line().encode(
        x="zeit:T",
        y="knockout:Q"
    )

    st.altair_chart(
        (line_index + line_knockout)
    )



    st.subheader("Aktuelle Kennzahlen")
    
    current_index_wert = df_selected_index.groupby("index_name")["index_wert"].last().round(3) # Letzter Wert bei GroupBy (gibt Serie an)
    current_index_wert = float(current_index_wert[selected_index]) # Filterung, da noch Serie vorliegt
    st.metric("Kurs", (current_index_wert), "Test")

    current_knockout = df_selected_index["knockout"].iloc[-1] # Positionsindex df.iloc[zeile, spalte] (nicht bei Gruppen/ Serie)
    current_knockout = float(round(current_knockout, 3))    
    st.metric("KnockOut", current_knockout, "Test" )