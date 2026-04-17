import streamlit as st
import pandas as pd
import numpy as np
from investment import Investment


def get_cumulative_investment_value(investments_list):
    total_value = 0
    for inv in investments_list:
        if inv.active:
            total_value += inv.get_investment_value()
    return total_value


@st.cache_data
def run_simulation(source, filter, selected_hebel, selected_budget, remaining_budget):
    df = source.copy()
    
    # Convert to numpy arrays for fast access (MAJOR PERFORMANCE IMPROVEMENT)
    index_values = df["index_wert"].values
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
                selected_hebel=selected_hebel,
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
            inv.update_hebel(i=i)
            inv.update_gewinn()

            if inv.get_hebel() == 0:
                inv.reset_investment(type="knockout")
                closing_date = df.loc[i, "date"]
                rows.append({
                    "date": df["date"].loc[i],
                    "inv_id": inv.id,
                    "gewinn": inv.get_gewinn(),
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
                    "gewinn": inv.get_gewinn(),
                    "closing_reason": inv.closing_reason,
                    "starting_investment": inv.starting_investment,
                    "active": inv.active,
                    "cumulative_investment_value": get_cumulative_investment_value(investments_list),
                    "closing_date": closing_date,
                })
                continue

            if inv.get_hebel() <= 1.5:
                inv.reset_investment(type="sell")
                closing_date = df.loc[i, "date"]
                rows.append({
                    "date": df["date"].loc[i],
                    "inv_id": inv.id,
                    "gewinn": inv.get_gewinn(),
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
                "hebel": inv.get_hebel(),
                "gewinn": inv.get_gewinn(),
                "closing_reason": inv.closing_reason,
                "starting_investment": inv.starting_investment,
                "active": inv.active,
                "cumulative_investment_value": get_cumulative_investment_value(investments_list),
                "starting_date": inv.starting_date,
            })
    df_investment = pd.DataFrame(rows)

    return investments_list, remaining_budget, df_investment


