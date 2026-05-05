import pandas as pd
from functions.df_functions import *
from classes.investment import Investment


def get_cumulative_investment_value(investments_list):
    total_value = 0
    for inv in investments_list:
        if inv.active:
            total_value += inv.get_investment_value()
    return total_value


#@st.cache_data
def run_simulation(source, filter, selected_leverage, selected_budget, remaining_budget):
    df = source.copy()
    
    # Convert to numpy arrays
    index_values = df["index_value"].values
    index_growth = df["index_growth"].values
    dates = df["date"].values

    rows = []
    investments_list = []
    investment_count = 0
    cumulative_value = 0

    for i in df[filter].index:

        if i % 20 == 0:
            remaining_budget += selected_budget


        if df.loc[i, "index_investpoint"]:
            
            investment_count += 1
            # Pass numpy arrays to Investment instead of dataframe
            new_inv = Investment(
                index_values=index_values,
                index_growth=index_growth,
                dates=dates,
                i=i,
                selected_leverage=selected_leverage,
                selected_budget=selected_budget,
                remaining_budget=remaining_budget,
                inv_id=investment_count)
            investments_list.append(new_inv)
            new_inv.start_investment()
            if new_inv.active:
                remaining_budget -= new_inv.get_investment_value()

        for inv in investments_list:

            if not inv.active:
                continue

            inv.update_current_knockout_barrier(i=i)
            inv.update_investment_value(i=i)
            inv.update_leverage(i=i)
            inv.update_profit()

            if inv.get_leverage() == 0:
                inv.reset_investment(type="knockout")
                closing_date = df.loc[i, "date"]
                rows.append({
                    "date": df["date"].loc[i],
                    "inv_id": inv.id,
                    "profit": inv.get_profit(),
                    "closing_reason": inv.closing_reason,
                    "starting_investment": inv.starting_investment,
                    "active": inv.active,
                    "cumulative_investment_value": get_cumulative_investment_value(investments_list),
                    "closing_date": closing_date,
                })
                continue

            if inv.get_investment_value() <= 0:
                inv.reset_investment(type="knockout")
                closing_date = df.loc[i, "date"]
                rows.append({
                    "date": df["date"].loc[i],
                    "inv_id": inv.id,
                    "profit": inv.get_profit(),
                    "closing_reason": inv.closing_reason,
                    "starting_investment": inv.starting_investment,
                    "active": inv.active,
                    "cumulative_investment_value": get_cumulative_investment_value(investments_list),
                    "closing_date": closing_date,
                })
                continue

            if inv.get_leverage() <= 1.5:
                inv.reset_investment(type="sell")
                closing_date = df.loc[i, "date"]
                rows.append({
                    "date": df["date"].loc[i],
                    "inv_id": inv.id,
                    "profit": inv.get_profit(),
                    "closing_reason": inv.closing_reason,
                    "starting_investment": inv.starting_investment,
                    "active": inv.active,
                    "cumulative_investment_value": get_cumulative_investment_value(investments_list),
                    "closing_date": closing_date,
                })
                continue

            rows.append({
                "date": df["date"].loc[i],
                "inv_id": inv.id,
                "knockout_barrier": inv.get_current_knockout_barrier(),
                "current_value": inv.get_investment_value(),
                "leverage": inv.get_leverage(),
                "profit": inv.get_profit(),
                "closing_reason": inv.closing_reason,
                "starting_investment": inv.starting_investment,
                "active": inv.active,
                "cumulative_investment_value": get_cumulative_investment_value(investments_list),
                "starting_date": inv.starting_date,
            })
    df_investment = pd.DataFrame(rows)

    return investments_list, remaining_budget, df_investment

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


