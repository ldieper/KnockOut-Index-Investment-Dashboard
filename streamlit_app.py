import streamlit as st
import pandas as pd
import altair as alt
from investment_simulation import run_simulation

st.set_page_config(layout="wide")

st.title("KnockOut-Investition auf Indizes")

#Init
if "selected_index" not in st.session_state:
    st.session_state.selected_index = "DAX"

if "selected_hebel" not in st.session_state:
    st.session_state.selected_hebel = 3.0

if "simulations_loaded" not in st.session_state:
    st.session_state.simulations_loaded = False

if "all_results" not in st.session_state:
    st.session_state.all_results = None


#Funktionen
def load_df(file_path):
    df = pd.read_json(file_path, orient="index")
    df.index = pd.to_datetime(df.index)
    df.columns = ["index_wert"]
    df.index.name = "date"
    return df.reset_index()


def prepare_investment_data(df_all_index):
    df_all_index["index_growth"] = df_all_index["index_wert"].pct_change().fillna(0)
    
    df_all_index["calculated_hebel"] = None
    df_all_index["calculated_knockout_barrier"] = None
    df_all_index["index_investpoint"] = None
    df_all_index['current_invest_wert'] = None

    df_all_index["yearly_high"] = (
        df_all_index["index_wert"]
            .rolling(window=252, min_periods=1)  # ~252 Handelstage = 1 Jahr
            .max()
    )

    start_date = df_all_index["date"].iloc[0] + pd.DateOffset(years=1)
    mask = df_all_index["date"] > start_date

    # Invest_Points setzen
    for i in df_all_index[mask].index:
        price = df_all_index.loc[i, "index_wert"]
        high = df_all_index.loc[i, "yearly_high"]

        if df_all_index["index_investpoint"].sum() == 0:
            if price < high * 0.9:
                df_all_index.loc[i, "index_investpoint"] = True
                continue

        if price < high * 0.9:
            if not df_all_index["index_investpoint"].iloc[max(0, i-20):i].any():
                df_all_index.loc[i, "index_investpoint"] = True
                continue

    return df_all_index, mask

# Kennzahlen berechnen (Funktion)
def calculate_metrics(df_investment):
    final_trades = df_investment.groupby("inv_id").last()

    active_trades = final_trades["active"].sum()

    closed_trades = (~final_trades["active"]).sum()
    sells_count = (final_trades["closing_reason"] == 1).sum()
    knockouts_count = (final_trades["closing_reason"] == 0).sum()

    trades_count = (final_trades["closing_reason"] != 2).sum()
    knockouts_count = (final_trades["closing_reason"] == 0).sum()
    sells_count = (final_trades["closing_reason"] == 1).sum()
    not_enough_money_count = (final_trades["closing_reason"] == 2).sum()
    active_trades = final_trades["active"].sum()

    final_gewinn = round(final_trades["gewinn"].sum(), 2)
    loss_sum = round(final_trades.loc[final_trades["closing_reason"] == 0, "starting_investment"].sum(), 2)
    total_invested_sum = round(final_trades.loc[final_trades["closing_reason"] != 2, "starting_investment"].sum(), 2)

    total_rendite = round(final_gewinn / total_invested_sum * 100, 2) if total_invested_sum > 0 else 0

    return {
        "closed_trades": closed_trades,
        "sells_count": sells_count,
        "knockouts_count": knockouts_count,
        "not_enough_money_count": not_enough_money_count,
        "final_gewinn": final_gewinn,
        "trades_count": trades_count,
        "active_trades": active_trades,
        "loss_sum": loss_sum,
        "total_invested_sum": total_invested_sum,
        "total_rendite": total_rendite,
    }


@st.cache_data
def precompute_all_simulations(debug_index=None, debug_hebels=None):
    index_map = {
        "DAX": "yfinance_indizes/^GDAXI.json",
        "S&P 500": "yfinance_indizes/^GSPC.json",
        "FSTE China 50": "yfinance_indizes/^HSI.json"
    }
    
    # Debug mit 1 Index und 1 Hebel
    if debug_index:
        index_map = {debug_index: index_map[debug_index]}
    
    hebels = debug_hebels if debug_hebels else [3, 5, 10]
    results = {}

    for index_name, file_path in index_map.items():
        df_all_index = load_df(file_path)
        df_all_index, mask = prepare_investment_data(df_all_index)

        selected_budget = 500
        remaining_budget = selected_budget

        for hebel in hebels:
            investments_list, remaining_budget, df_investment = run_simulation(
                df_all_index,
                mask,
                hebel,
                selected_budget,
                remaining_budget  
            )

            # Kennzahlen berechnen
            metrics = calculate_metrics(df_investment)

            # Plotten
            df_plot = pd.merge(
                df_all_index,
                df_investment[["date", "current_value", "inv_id", "knockout_barrier", "hebel", "gewinn", "cumulative_investment_value", "starting_date", "closing_date"]],
                on="date",
                how="left"
            )

            cumulative_value = df_investment["cumulative_investment_value"].iloc[-1]

            key = (index_name, hebel)
            results[key] = {
                "df_all_index": df_all_index,
                "df_investment": df_investment,
                "df_plot": df_plot,
                "remaining_budget": remaining_budget,  
                "cumulative_value": cumulative_value,
                "metrics": metrics,
            }

    return results


#"Loading Screen"
if not st.session_state.simulations_loaded:
    with st.spinner("Precomputing.. Das dauert bis zu 3 Minuten. Ein guter Moment um neuen Kaffe zu holen. ☕"):
        # DEBUG: Ändere hier für schnelleres Debuggen
        st.session_state.all_results = precompute_all_simulations(debug_index="DAX", debug_hebels=[3]) #ohne Debug func()
        st.session_state.simulations_loaded = True
    st.rerun()


#Abspeichern der berechneten und aktuellen Daten
current = st.session_state.all_results[(st.session_state.selected_index, st.session_state.selected_hebel)]

df_all_index = current["df_all_index"]
df_investment = current["df_investment"]
df_plot = current["df_plot"]
remaining_budget = current["remaining_budget"]
cumulative_value = current["cumulative_value"]
metrics = current["metrics"]


#Layout / UI
top = st.container(border=True)
mid = st.container(border=True)
bottom = st.container(border=True)

with top:
    st.subheader(f"Kursverlauf - {st.session_state.selected_index}")

    base = alt.Chart(df_plot).encode(
        x=alt.X("date:T", title="Datum", axis=alt.Axis(format="%d %b %y"))
    )

    left_axis_group = alt.layer(
        base.mark_line(color="#BA2BAC").encode(
            y=alt.Y("index_wert:Q", title="Index & Barrier Level")
        ),

        base.mark_line(color="#c4265e").encode(
            y="knockout_barrier:Q",
            detail="inv_id:N"
        ).transform_calculate(
            abs_dist="abs(datum.index_wert - datum.knockout_barrier)"
        ).transform_window(
            rank="rank(abs_dist)",
            sort=[alt.SortField("abs_dist", order="ascending")],
            groupby=["date"]
        ).transform_filter(
            alt.datum.rank <= 2
        )
    )

    right_axis_group = alt.Chart(df_investment).mark_line(color="#e2e22e", size=2).encode(
        x="date:T",
        y=alt.Y("cumulative_investment_value:Q", title="Investment Value (€)"),
    )

    combined_chart = alt.layer(
        left_axis_group,
        right_axis_group
    ).resolve_scale(
        y="independent"
    )
    st.altair_chart(combined_chart, width="stretch")


with mid:

    mid_left, mid_right = st.columns([0.35, 0.65])

    df_filtered = df_investment[df_investment["closing_reason"] != 2].copy()
    df_filtered = df_filtered.groupby("inv_id").last().reset_index(drop=False)

    df_filtered["starting_date"] = df_filtered["starting_date"].dt.strftime("%d.%m.%y")
    df_filtered["closing_date"] = df_filtered["closing_date"].dt.strftime("%d.%m.%y")

    df_filtered["current_value"] = df_filtered["current_value"].where(df_filtered["active"], 0)

    df_filtered = df_filtered.sort_values(by=["active", "inv_id"], ascending=True)

    with mid_left:
        st.subheader("Investitionen")


        event = st.dataframe(
            df_filtered[["inv_id", "active", "starting_date", "closing_date", "closing_reason", "gewinn", "current_value"]],
            hide_index=True,
            width="stretch",
            on_select="rerun",
            selection_mode="single-row"
        )

    selected_row = None

    if event.selection.rows:
        selected_row = event.selection.rows[0]
    else:
        selected_row = 0 if len(df_filtered) > 0 else None  # Default: erste Zeile

    
    with mid_right:
        st.subheader("Details zum Investment")
        st.write(f"**Investment ID:** {df_filtered.loc[selected_row, 'inv_id']}")



with bottom:

    st.markdown("""
    <style>

    div[data-testid="stMetric"] {
        padding: 12px;
        /* border: 2px solid red; */
        /* border-radius: 14px; */
        /* box-shadow: 0 2px 10px rgba(0,0,0,0.08); */
        transition: all 0.2s ease;
    }

    div[data-testid="stMetric"]:hover {
        transform: translateY(-4px) scale(1.02);
        box-shadow: 0 8px 25px rgba(0,0,0,0.15);
    }

    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="blue-section">', unsafe_allow_html=True)


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
                st.metric("Gewinn", f"€ {metrics['final_gewinn']:,.2f}".replace(",", " "), "Test")
                st.metric("Verkäufe (Hebel < 1.5x)", f"{metrics['sells_count']}", "Test")

            with col3:
                st.metric("Verluste", f"€ {metrics['loss_sum']:,.2f}".replace(",", " "), "Test")
                st.metric("KnockOut", f"{metrics['knockouts_count']}", "Test")

            with col4:
                st.metric("Rendite", f"{metrics['total_rendite']} %", "Test")
                st.metric("Anzahl aktiver Investments", f"{metrics['active_trades']}", "Test")

            with col5:
                st.metric("Verfügbares Budget", f"€ {remaining_budget:,.2f}".replace(",", " "), "Test")
                st.metric("Monatliches Budget", f"€ 500,00", "Test")
                #st.metric("Anzahl nicht ausgeführter Investments (zu wenig Budget)", f"{metrics['not_enough_money_count']}", "Test")

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


    st.markdown('</div>', unsafe_allow_html=True)