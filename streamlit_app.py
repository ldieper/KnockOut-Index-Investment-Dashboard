import streamlit as st
import pandas as pd
import altair as alt
from pathlib import Path
from investment_simulation import run_simulation
from yfinance_loader import download
import duckdb
import pickle # Any to bytes

st.set_page_config(layout="wide")

st.title("KnockOut-Investments on indices")

#Extracts the index name and file path from the "index_data" folder, returns a dictionary mapping index names to file paths
def get_index_map(folder="index_data"):
    index_map = {}
    
    for file in Path(folder).glob("*.json"):
        # Use filename (without extension) as default name
        name = file.stem
        
        name = name.replace("^", "")  # remove ^ if present
        
        index_map[name] = str(file)
    
    return index_map


#Init
index_map = get_index_map()

if "selected_index" not in st.session_state:
    st.session_state.selected_index = list(index_map.keys())[0]

if "selected_leverage" not in st.session_state:
    st.session_state.selected_leverage = 3

if "simulations_loaded" not in st.session_state:
    st.session_state.simulations_loaded = False

if "all_results" not in st.session_state:
    st.session_state.all_results = None


#Funktionen
#@st.cache_data
def load_df(file_path):
    df = pd.read_json(file_path, orient="index")
    df.index = pd.to_datetime(df.index)
    df.columns = ["index_value"]
    df.index.name = "date"
    return df.reset_index()

def prepare_investment_data(df_all_index):
    df_all_index["index_growth"] = df_all_index["index_value"].pct_change().fillna(0)
    
    df_all_index["index_investpoint"] = None

    df_all_index["yearly_high"] = (
        df_all_index["index_value"]
            .rolling(window=252, min_periods=1)  # ~252 Trading Days = 1 Year
            .max()
    )

    start_date = df_all_index["date"].iloc[0] + pd.DateOffset(years=1) #Starts one year in, so the 52-week high can be used as reference point
    mask = df_all_index["date"] > start_date

    # Adding investmentpoints 
    for i in df_all_index[mask].index:
        price = df_all_index.loc[i, "index_value"]
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

# Calcuating metrics of the final Investments
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

    final_profit = round(final_trades["profit"].sum(), 2)
    loss_sum = round(final_trades.loc[final_trades["closing_reason"] == 0, "starting_investment"].sum(), 2)
    total_invested_sum = round(final_trades.loc[final_trades["closing_reason"] != 2, "starting_investment"].sum(), 2)

    total_return = round(final_profit / total_invested_sum * 100, 2) if total_invested_sum > 0 else 0

    return {
        "closed_trades": closed_trades,
        "sells_count": sells_count,
        "knockouts_count": knockouts_count,
        "not_enough_money_count": not_enough_money_count,
        "final_profit": final_profit,
        "trades_count": trades_count,
        "active_trades": active_trades,
        "loss_sum": loss_sum,
        "total_invested_sum": total_invested_sum,
        "total_return": total_return,
    }


def load_from_db():
    try:
        con = duckdb.connect('simulations.db')
        # Check if table exists
        if not con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='simulations'").fetchone():
            con.close()
            return None
        
        # Load data
        df = con.execute("SELECT * FROM simulations").fetchdf()
        results = {}
        for _, row in df.iterrows(): #"_" because index like 0,1,2,3 is not needed (trying some new mechanics)
            key = (row['index_name'], row['leverage'])
            results[key] = {
                'df_all_index': pickle.loads(row['df_all_index_pickle']),
                'df_investment': pickle.loads(row['df_investment_pickle']),
                'df_plot': pickle.loads(row['df_plot_pickle']),
                'df_table': pickle.loads(row['df_table_pickle']),
                'remaining_budget': row['remaining_budget'],
                'cumulative_value': row['cumulative_value'],
                'metrics': pickle.loads(row['metrics_pickle'])
            }
        
        # Check if all combinations exist
        index_map = get_index_map()
        expected_keys = {(index_name, leverage) for index_name in index_map.keys() for leverage in [3, 5, 10]}
        if set(results.keys()) != expected_keys:
            con.close()
            return None
        
        con.close()
        return results
    
    except Exception as error_message:
        print(f"Error loading from DB: {error_message}")
        return None


def store_to_db(results):
    con = duckdb.connect('simulations.db')
    con.execute("DROP TABLE IF EXISTS simulations")
    con.execute("CREATE TABLE simulations (index_name VARCHAR, leverage INTEGER, df_all_index_pickle BLOB, df_investment_pickle BLOB, df_plot_pickle BLOB, df_table_pickle BLOB, remaining_budget DOUBLE, cumulative_value DOUBLE, metrics_pickle BLOB)")
    for key, value in results.items():
        index_name, leverage = key
        con.execute("INSERT INTO simulations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", [
            index_name,
            leverage,
            pickle.dumps(value['df_all_index']),
            pickle.dumps(value['df_investment']),
            pickle.dumps(value['df_plot']),
            pickle.dumps(value['df_table']),
            value['remaining_budget'],
            value['cumulative_value'],
            pickle.dumps(value['metrics'])
        ])
    con.close()


# Function for creating plot of individual investments
def create_investment_detail_plot(df_investment, df_all_index, inv_id):
    if inv_id is None:
        return None
    
    # Filter to only this investment
    df_inv = df_investment[df_investment["inv_id"] == inv_id][["date", "current_value", "leverage", "knockout_barrier"]].copy()
    
    if df_inv.empty:
        return None
    
    # Merge with index data for comparison
    df_plot_detail = pd.merge(
        df_all_index[["date", "index_value"]],
        df_inv,
        on="date",
        how="inner"
    )

    legend = alt.Legend(
    orient="top"
    )

    color = alt.Color(
        "lines:N",
        legend=legend,
        scale=alt.Scale(
            domain=["Index", "Barrier", "Investment"],
            range=["#BA2BAC", "#c4265e", "#e2e22e"]
        )
    )
    
    # Create base chart with X axis
    base = alt.Chart(df_plot_detail).encode(
        x=alt.X("date:T", title="Datum", axis=alt.Axis(format="%d %b %y"))
    )
    
    # LEFT AXIS: Index value and Knockout barrier
    line_index = base.transform_calculate(
        lines="'Index'"
        ).mark_line(size=2).encode(
            y=alt.Y("index_value:Q", title="Index & Barrier Value", scale=alt.Scale(zero=False)),
            color=color
    )
    
    line_barrier = base.transform_calculate(
        lines="'Barrier'"
        ).mark_line(strokeDash=[5, 5], size=2).encode(   
            y=alt.Y("knockout_barrier:Q", scale=alt.Scale(zero=False)),
            color=color
    )
    
    # RIGHT AXIS: Investment value (independent scale)
    line_investment = base.transform_calculate(
        lines="'Investment'"
        ).mark_line(size=2.5).encode(
            y=alt.Y("current_value:Q", title="Investment Value (€)", scale=alt.Scale(zero=False), axis=alt.Axis(orient="right")),
            color=color
    )
    

    left_chart = alt.layer(line_index, line_barrier)
    
    chart = alt.layer(left_chart, line_investment).resolve_scale(
        y="independent"
    ).properties(
        height=250,
        title=f"Investment: {int(inv_id)}",
    )
    
    return chart


def filter_nearest_barriers(df_plot, top_n=2):
    if "knockout_barrier" not in df_plot.columns or df_plot["knockout_barrier"].isna().all():
        return df_plot
    
    # Calculate absolute distance from index to barrier
    abs_dist = (df_plot["index_value"] - df_plot["knockout_barrier"]).abs()
    
    # Rank by distance within each date group, keep only top N (defaut = 2)
    rank = df_plot.groupby("date").cumcount()
    df_plot_temp = df_plot.assign(abs_dist=abs_dist, rank=rank)
    df_plot_temp["rank"] = df_plot_temp.groupby("date")["abs_dist"].rank(method="first")
    
    return df_plot_temp[df_plot_temp["rank"] <= top_n].drop(columns=["abs_dist", "rank"])


#@st.cache_data
def precompute_all_simulations(debug_index=None, debug_leverages=None): #debug_index="GDAXI", debug_leverages=3
    index_map = get_index_map()

    if debug_index:
        index_map = {debug_index: index_map[debug_index]}

    leverages = [debug_leverages] if debug_leverages else [3, 5, 10]
    results = {}

    for index_name, file_path in index_map.items():
        df_all_index = load_df(file_path)
        df_all_index, mask = prepare_investment_data(df_all_index)

        selected_budget = 500
        remaining_budget = selected_budget

        for leverage in leverages:
            investments_list, remaining_budget, df_investment = run_simulation(
                df_all_index,
                mask,
                leverage,
                selected_budget,
                remaining_budget  
            )

            # Calculate metrics
            metrics = calculate_metrics(df_investment)

            df_investment_plot = df_investment[["date", "current_value", "inv_id", "knockout_barrier", "leverage", "profit", "cumulative_investment_value", "starting_date", "closing_date"]].drop_duplicates(subset=["date", "inv_id"], keep="last")
            
            #left join with df_all_index on mathing dates
            df_plot = pd.merge(
                df_all_index,
                df_investment_plot,
                on="date",
                how="left"
            )
            
            df_table = df_investment[df_investment["closing_reason"] != 2][["inv_id", "active", "closing_reason", "starting_date", "closing_date", "profit", "current_value", "starting_investment"]].copy()
            df_table = df_table.groupby("inv_id").last().reset_index(drop=False)
            df_table["starting_date"] = df_table["starting_date"].dt.strftime("%d.%m.%y")
            df_table["closing_date"] = df_table["closing_date"].dt.strftime("%d.%m.%y")
            df_table["current_value"] = df_table["current_value"].where(df_table["active"], 0)
            df_table = df_table.sort_values(by=["inv_id"], ascending=True)

            cumulative_value = df_investment["cumulative_investment_value"].iloc[-1]

            key = (index_name, leverage)
            results[key] = {
                "df_all_index": df_all_index,
                "df_investment": df_investment,
                "df_plot": df_plot,
                "df_table": df_table,
                "remaining_budget": remaining_budget,  
                "cumulative_value": cumulative_value,
                "metrics": metrics,
            }

    return results


#"Loading Screen"

#st.button("Load new data")
#download(tickers=["^GDAXI", "^GSPC", "^HSI"])

#st.button("Load historic data")



if not st.session_state.simulations_loaded:
    st.session_state.all_results = load_from_db()
    if st.session_state.all_results is None:
        with st.spinner("Precomputing.. This may take up to 1:30 minutes. A brilliant moment for some coffee. ☕"):
            st.session_state.all_results = precompute_all_simulations()
            store_to_db(st.session_state.all_results)
    st.session_state.simulations_loaded = True
    st.rerun()


#Storing calculations in current
current = st.session_state.all_results[(st.session_state.selected_index, st.session_state.selected_leverage)]

#assigning current to variables
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
    st.subheader(f"Index performance - {st.session_state.selected_index}")

    df_plot_filtered = filter_nearest_barriers(df_plot, top_n=2)

    legend = alt.Legend(
        orient="none",
        legendX=10,
        legendY=10
    )

    base = alt.Chart(df_plot_filtered).encode(
        x=alt.X("date:T", title="Datum", axis=alt.Axis(format="%d %b %y"))
    )

    left_axis_group = alt.layer(
        base.transform_calculate(lines="'Index'").mark_line().encode(
            y=alt.Y("index_value:Q", title="Index & Barrier Level"),
            color=alt.Color("lines:N", legend=legend,
                            scale=alt.Scale(domain=["Index", "Barrier", "Investment"],
                                            range=["#BA2BAC", "#c4265e", "#e2e22e"]))
        ),

        base.transform_calculate(lines="'Barrier'").mark_line().encode(
            y="knockout_barrier:Q",
            detail="inv_id:N",
            color=alt.Color("lines:N", legend=None)
        )
    )

    right_axis_group = alt.Chart(df_investment).transform_calculate(
        lines="'Investment'"
    ).mark_line(size=2).encode(
        x="date:T",
        y=alt.Y("cumulative_investment_value:Q", title="Investment Value (€)"),
        color=alt.Color(
            "lines:N",
            scale=alt.Scale(
                domain=["Investment"],
                range=["#e2e22e"]
            ),
            legend=None
        )
    )

    combined_chart = alt.layer(
        left_axis_group,
        right_axis_group
    ).resolve_scale(
        y="independent"
    )

    st.altair_chart(combined_chart, width="stretch")
    

with mid:

    st.markdown("""
    <style>

    div[data-testid="stMetric"] {
        padding: 12px;
        border: 2px solid transparent;
        border-radius: 14px;
        /* box-shadow: 0 2px 10px rgba(0,0,0,0.08); */
        transition: all 0.2s ease;
    }

    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px) scale(1.02);
        border: 2px solid #3D4044;
        box-shadow: 0 8px 25px rgba(0,0,0,0.15);
    }

    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="blue-section">', unsafe_allow_html=True)


    mid_left, mid_right = st.columns([0.7, 0.3])

    with mid_left:

        with st.container(border=True):

            st.subheader("Current metrics")

            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:
                st.metric("Investment-Level", f"€ {round(cumulative_value, 2):,.2f}".replace(",", " "))
                current_index_value = float(df_all_index["index_value"].iloc[-1])
                st.metric("Index-Level", f"{current_index_value:,.3f}".replace(",", " "))

            with col2:
                st.metric("Profit", f"€ {metrics['final_profit']:,.2f}".replace(",", " "))
                st.metric("Sells (Leverage < 1.5x)", f"{metrics['sells_count']}", f"{round( (metrics['sells_count'] / metrics['trades_count'] if not 0 else 1) * 100, 2 )} % of total", delta_arrow="off")

            with col3:
                st.metric("Losses", f"€ {metrics['loss_sum']:,.2f}".replace(",", " "))
                st.metric("KnockOuts", f"{metrics['knockouts_count']}", f"{round( (metrics['knockouts_count'] / metrics['trades_count'] if not 0 else 1) * 100, 2 )} % of total", delta_color="inverse", delta_arrow="off")

            with col4:
                st.metric("ROI", f"{metrics['total_return']} %", )
                st.metric("Active investments", f"{metrics['active_trades']}", f"{round( (metrics['active_trades'] / metrics['trades_count'] if not 0 else 1) * 100, 2 )} % of total" , delta_arrow="off")

            with col5:
                st.metric("Accessible budget", f"€ {remaining_budget:,.2f}".replace(",", " "))
                st.metric("Monthly budget", f"€ 500,00")
                #st.metric("Anzahl nicht ausgeführter Investments (zu wenig Budget)", f"{metrics['not_enough_money_count']}", "Test")

    with mid_right:
        with st.container(border=True):

            st.subheader("Settings")

            col1, col2 = st.columns(2)

            index_map = get_index_map()

            with col1:
                st.radio(
                    "Index",
                    list(index_map.keys()),
                    key="selected_index"
                )

            with col2:
                st.radio(
                    "Leverage",
                    [3, 5, 10],
                    key="selected_leverage"
                )


    st.markdown('</div>', unsafe_allow_html=True)


with bottom:

    bottom_left, bottom_right = st.columns([0.12, 0.88])

    df_filtered = current["df_table"]

    with bottom_left:
        st.subheader("Investments")

        closing_reason_map = {0.0: "KnockOut", 1.0: "Sold", 2.0: "No Money", None: "Active"}
        
        # Add mapped closing_reason column to display
        df_display = df_filtered.copy()
        df_display["closing_reason"] = df_display["closing_reason"].apply(
            lambda x: closing_reason_map.get(float(x), "Unbekannt") if pd.notna(x) else "Aktiv"
        )
        
        event = st.dataframe(
            df_display[["inv_id", "closing_reason"]],
            hide_index=True,
            width="stretch",
            on_select="rerun",
            selection_mode="single-row"
        )

        selected_row = None
        if event.selection.rows:
            selected_row = event.selection.rows[0]
        else:
            selected_row = 0 if len(df_filtered) > 0 else None  # Default: 1st row

    
    with bottom_right:
        st.subheader("Detailed view of Investments")

        if selected_row is not None and selected_row < len(df_filtered):
            selected_inv_id = df_filtered.iloc[selected_row]['inv_id']
            
            # Create and display the investment detail chart
            detail_chart = create_investment_detail_plot(df_investment, df_all_index, selected_inv_id)
            if detail_chart:
                st.altair_chart(detail_chart, width="stretch")
            
            selected_row_data = df_filtered.iloc[selected_row]
            
            # Map closing reason to readable text
            closing_reason_value = selected_row_data['closing_reason']
            if closing_reason_value is None or pd.isna(closing_reason_value):
                closing_reason_text = "Active"
            else:
                closing_reason_text = closing_reason_map.get(float(closing_reason_value), "Unknown")
            

            col1, col2, col3 ,col4, col5, col6 = st.columns(6)

            # Displaying metrics (formatted)
            with col1:
                starting_date = selected_row_data['starting_date']
                st.metric("Start", f"{starting_date}")

            with col2:
                starting_investment = round(selected_row_data['starting_investment'], 2)
                st.metric("Start-Value", f"€ {starting_investment}")

            with col3:
                if selected_row_data['active']:
                    current_value = selected_row_data['current_value']
                    st.metric("Current Value", f"€ {current_value:,.2f}".replace(",", " "))

                elif not selected_row_data['active']:
                    closing_date = selected_row_data['closing_date']
                    st.metric("End", f" {closing_date}")

            with col4:
                st.metric("Status", closing_reason_text)

            with col5:
                profit_value = selected_row_data['profit']
                st.metric("Profit", f"€ {profit_value:,.2f}".replace(",", " "))

            with col6:
                indiv_return  = round( ((profit_value / starting_investment if starting_investment != 0 else 0)*100), 2)   
                st.metric("ROI", f"{indiv_return} %")
                
        else:
            st.info("Choose an investment from the table")



