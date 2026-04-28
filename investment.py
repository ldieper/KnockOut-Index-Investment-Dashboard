import numpy as np
from numpy import floor


class Investment:
    
    def __init__(self, index_values, index_growth, dates, i, selected_hebel, selected_budget, remaining_budget, inv_id):
        self.index_values = index_values  
        self.index_growth = index_growth  
        self.dates = dates 
        
        self.i = i
        self.id = inv_id
        self.selected_hebel = selected_hebel
        self.selected_budget = selected_budget
        self.remaining_budget = remaining_budget

        self.starting_date = self.dates[self.i]
        self.active = False
        self.closing_reason = None  # 0 = Knockout, 1 = Sell, 2 = Not_enough_money
        self.starting_investment = 0.0
        self.investment_value = 0.0
        self.price_of_option = 0.0
        self.possible_amount_of_options = 0
        self.hebel = 0.0
        self.current_knockout_barrier = 0.0
        self.gewinn = 0.0


    def start_investment(self):
        self.update_current_knockout_barrier(i=self.i)
        self.update_hebel(i=self.i)

        abstand = self.index_values[self.i] - self.get_current_knockout_barrier()
        price_of_option = abstand * 0.01

        max_accessible_budget = self.selected_budget * 1
        actual_invested_budget = min(max_accessible_budget, self.remaining_budget)

        if actual_invested_budget < price_of_option:
            self.reset_investment(type="not_enough_money")
            return
        
        self.active = True

        possible_amount_of_options = floor(actual_invested_budget / price_of_option)
        self.investment_value = possible_amount_of_options * price_of_option
        self.starting_investment = self.investment_value





    def reset_investment(self, type):
        self.active = False
        self.investment_value = None
        self.current_knockout_barrier = None

        if type == "knockout":
            self.closing_reason = 0
            self.gewinn = -self.starting_investment
        elif type == "sell": 
            self.closing_reason = 1
        elif type == "not_enough_money": 
            self.closing_reason = 2


    def get_current_knockout_barrier(self):
        return round(self.current_knockout_barrier, 3)

    def update_current_knockout_barrier(self, i):
        if i == self.i:
            self.current_knockout_barrier = (
                self.index_values[self.i] * (1 - 1 / self.selected_hebel)
            )
        elif i > self.i:
            knockout_daily_increase = (self.current_knockout_barrier * 0.05) / 360
            self.current_knockout_barrier += knockout_daily_increase


    def get_hebel(self):
        return min(self.hebel, 100)
    
    def update_hebel(self, i):
        if i == self.i:
            self.hebel = self.selected_hebel
        
        if i > self.i:
            abstand = self.index_values[i] - self.get_current_knockout_barrier()
            hebel = self.index_values[i] / abstand if abstand > 0 else 0
            self.hebel = min(hebel, 100)


    def get_investment_value(self):
        return self.investment_value

    def update_investment_value(self, i):
        if i == self.i:
            self.investment_value = self.starting_investment

        if self.get_hebel() == 0:
            self.investment_value = 0
            return

        growth = 1 + self.index_growth[i] * self.get_hebel()
        self.investment_value *= growth
    
    
    def get_gewinn(self):
        return self.gewinn
    
    def update_gewinn(self):
        self.gewinn = round(self.get_investment_value() - self.starting_investment, 2)