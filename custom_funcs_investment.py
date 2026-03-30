from numpy import floor

def start_investment(df_all_index, state, i, selected_hebel, selected_budget, remaining_budget):
        
        df_all_index.loc[i, "calculated_knockout_barrier"] = df_all_index.loc[i, "index_wert"] * (1 - 1 / selected_hebel)
        

        abstand = df_all_index.loc[i, "index_wert"] - df_all_index.loc[i, "calculated_knockout_barrier"]
        price_of_option = abstand * state["bezugsverhältnis"]

        max_accessible_budget = selected_budget * 0.2 # 20% von ausgesuchtem Budget (von 1000€ -> 200€)
        actual_invested_budget = min(max_accessible_budget, remaining_budget) #(200€, 200 - possible_amount_of_options * price_of_option)

        if actual_invested_budget < price_of_option:
            state["fault_not_enough_budget"] = True
            return


        df_all_index.loc[i, "calculated_hebel"] = selected_hebel

        state["is_invested"] = True
        state["trades_count"] += 1


        df_all_index.loc[i, "actual_invested_budget"] = actual_invested_budget


        df_all_index.loc[i, "price_of_option"] = price_of_option

        possible_amout_of_options = floor(actual_invested_budget / price_of_option)

        df_all_index.loc[i, "possible_amount_of_options"] = possible_amout_of_options
        
        state["active_investment"] = possible_amout_of_options * price_of_option
        remaining_budget = remaining_budget - state["active_investment"]

        df_all_index.loc[i, "active_investment"] = state["active_investment"]
        df_all_index.loc[i, "current_invest_wert"] = state["active_investment"]
        state["index_investpoint_wert"] = state["active_investment"]

def knockout(df_all_index, state, i):
        global is_invested, knockout_count, active_investment
        active_investment = None
        df_all_index.loc[i, "current_invest_wert"] = None
        df_all_index.loc[i, "calculated_hebel"] = 0.0
        df_all_index.loc[i, "calculated_knockout_barrier"] = None
        state["is_invested"] = False
        state["knockout_count"] += 1

def reset_investment(df_all_index, state, i):
        global is_invested, active_investment, sells_count
        active_investment = None
        df_all_index.loc[i, "current_invest_wert"] = None
        df_all_index.loc[i, "calculated_hebel"] = 0.0
        df_all_index.loc[i, "calculated_knockout_barrier"] = None
        state["is_invested"] = False
        state["sells_count"] += 1

def get_knockout_barrier(df_all_index, i):
            prev_knockout_barrier = df_all_index.loc[i-1, "calculated_knockout_barrier"]
            knockout_daily_increase = (prev_knockout_barrier * 0.05) / 360
            return round(prev_knockout_barrier + knockout_daily_increase, 3)

def get_hebel(df_all_index, i):
            abstand = df_all_index.loc[i, "index_wert"] - df_all_index.loc[i, "calculated_knockout_barrier"]
            if abstand > 0:
                return df_all_index.loc[i, "index_wert"] / abstand
            else:   
                return 0
            
def get_active_investment(df_all_index, i, state):
            current_growth = 1 + (df_all_index.loc[i, "index_growth"] * df_all_index.loc[i, "calculated_hebel"])
            return state["active_investment"] * current_growth

def get_rendite(state):
            return round(state["active_investment"] - state["index_investpoint_wert"], 3)