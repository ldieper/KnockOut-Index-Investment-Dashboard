from numpy import floor

class investment:
    def __init__(self, source, state, i, selected_hebel, selected_budget, remaining_budget, inv_id):
        self.source = source
        self.state = state
        self.i = i
        self.id = inv_id
        self.selected_hebel = selected_hebel
        self.selected_budget = selected_budget #kann reduziert werden
        self.remaining_budget = remaining_budget #am Ende anpassen und nicht immer übergeben werden. (wird ja erst beim investment verändert!)
        
        self.active_investment = 0.0
        self.current_knockout_barrier = 0.0
        self.price_of_option = 0.0
        self.possible_amount_of_options = 0

    def start_investment(self):
        # calculate knockout barrier
        self.source.loc[self.i, "calculated_knockout_barrier"] = (
            self.source.loc[self.i, "index_wert"] * (1 - 1 / self.selected_hebel)
        )

        self.current_knockout_barrier = self.source.loc[self.i, "calculated_knockout_barrier"]

        abstand = self.source.loc[self.i, "index_wert"] - self.source.loc[self.i, "calculated_knockout_barrier"]
        price_of_option = abstand * self.state["bezugsverhältnis"]

        max_accessible_budget = self.selected_budget * 0.2
        actual_invested_budget = min(max_accessible_budget, self.remaining_budget)

        if actual_invested_budget < price_of_option:
            self.state["fault_not_enough_budget"] = True
            return

        self.source.loc[self.i, "calculated_hebel"] = self.selected_hebel
        self.state["is_invested"] = True
        self.state["trades_count"] += 1

        #self.source.loc[self.i, "actual_invested_budget"] = actual_invested_budget
        #self.source.loc[self.i, "price_of_option"] = price_of_option

        possible_amount_of_options = floor(actual_invested_budget / price_of_option)
        #self.source.loc[self.i, "possible_amount_of_options"] = possible_amount_of_options

        self.state["active_investment"] = possible_amount_of_options * price_of_option
        self.remaining_budget -= self.state["active_investment"]

        self.source.loc[self.i, "active_investment"] = self.state["active_investment"]
        self.source.loc[self.i, "current_invest_wert"] = self.state["active_investment"]
        self.state["index_investpoint_wert"] = self.state["active_investment"]

    def reset_investment(self, type):
        self.active_investment = None
        self.source.loc[self.i, "current_invest_wert"] = None
        self.source.loc[self.i, "calculated_hebel"] = 0.0
        self.source.loc[self.i, "calculated_knockout_barrier"] = None
        self.state["is_invested"] = False
        if type == "sell":
            self.state["sells_count"] += 1
        elif type == "knockout":
            self.state["knockout_count"] += 1


    def get_knockout_barrier(self):
        prev_knockout_barrier = self.source.loc[self.i-1, "calculated_knockout_barrier"]
        knockout_daily_increase = (prev_knockout_barrier * 0.05) / 360
        return round(prev_knockout_barrier + knockout_daily_increase, 3)

    def get_hebel(self):
        abstand = self.source.loc[self.i, "index_wert"] - self.current_knockout_barrier
        return self.source.loc[self.i, "index_wert"] / abstand if abstand > 0 else 0
                
    def get_active_investment(self):
        current_growth = 1 + (self.source.loc[self.i, "index_growth"] * self.source.loc[self.i, "calculated_hebel"])
        return self.state["active_investment"] * current_growth

    def get_rendite(self):
        return round(self.state["active_investment"] - self.state["index_investpoint_wert"], 3)