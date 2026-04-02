from numpy import floor

class investment:
    def __init__(self, source, state, i, selected_hebel, selected_budget, remaining_budget):
        self.source = source
        self.state = state
        self.i = i
        self.selected_hebel = selected_hebel
        self.selected_budget = selected_budget #kann reduziert werden
        self.remaining_budget = remaining_budget #am Ende anpassen und nicht immer übergeben werden. (wird ja erst beim investment verändert!)

    def start_investment(self):
        # calculate knockout barrier
        self.source.loc[self.i, "calculated_knockout_barrier"] = (
            self.source.loc[self.i, "index_wert"] * (1 - 1 / self.selected_hebel)
        )

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

        self.source.loc[self.i, "actual_invested_budget"] = actual_invested_budget
        self.source.loc[self.i, "price_of_option"] = price_of_option

        possible_amount_of_options = floor(actual_invested_budget / price_of_option)
        self.source.loc[self.i, "possible_amount_of_options"] = possible_amount_of_options

        self.state["active_investment"] = possible_amount_of_options * price_of_option
        self.remaining_budget -= self.state["active_investment"]

        self.source.loc[self.i, "active_investment"] = self.state["active_investment"]
        self.source.loc[self.i, "current_invest_wert"] = self.state["active_investment"]
        self.state["index_investpoint_wert"] = self.state["active_investment"]