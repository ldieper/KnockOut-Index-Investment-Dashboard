from numpy import floor

class Investment:
        def __init__(self, source, i, selected_hebel, selected_budget, remaining_budget, inv_id):
            self.source = source
            self.i = i
            self.id = inv_id
            self.selected_hebel = selected_hebel
            self.selected_budget = selected_budget #kann reduziert werden
            self.remaining_budget = remaining_budget #am Ende anpassen und nicht immer übergeben werden. (wird ja erst beim investment verändert!)

            self.starting_date = self.source.loc[self.i, "date"]
            self.active = False
            self.closing_reason = None #0 = Knockout, 1 = Sell, 2 = Not_enough_money
            self.starting_investment = 0.0
            self.investment_value = 0.0
            self.price_of_option = 0.0
            self.possible_amount_of_options = 0
            self.hebel = 0.0
            self.current_knockout_barrier = 0.0
            self.gewinn = 0.0


        def start_investment(self):

            self.update_current_knockout_barrier(i=self.i) #setzt die Knockoutbarriere zum Startzeitpunkt
            self.update_hebel(i=self.i) #setzt den Hebel zum Startzeitpunkt

            abstand = self.source.loc[self.i, "index_wert"] - self.get_current_knockout_barrier()
            price_of_option = abstand * 0.01 #Bezugsverhältnis

            max_accessible_budget = self.selected_budget * 0.5
            actual_invested_budget = min(max_accessible_budget, self.remaining_budget)

            if actual_invested_budget < price_of_option:
                self.reset_investment(type="not_enough_money") #Setzt die Investition als inaktiv, da nicht genug Geld für den Kauf einer Option vorhanden ist
                return
            
            self.active = True #setzt die Investition als aktiv 

            possible_amount_of_options = floor(actual_invested_budget / price_of_option)
            self.investment_value = possible_amount_of_options * price_of_option
            self.starting_investment = self.investment_value #Für die späteren Renditeberechnung


        def reset_investment(self, type):
            self.active = False
            self.investment_value = None
            self.current_knockout_barrier = None

            if type == "knockout":
                self.closing_reason = 0
            elif type == "sell": 
                self.closing_reason = 1
            elif type == "not_enough_money": 
                self.closing_reason = 2


        def get_current_knockout_barrier(self):
            return round(self.current_knockout_barrier, 3)

        def update_current_knockout_barrier(self, i):
            if i == self.i:
                self.current_knockout_barrier = (
                    self.source.loc[self.i, "index_wert"] * (1 - 1 / self.selected_hebel)
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
                abstand = self.source.loc[i, "index_wert"] - self.get_current_knockout_barrier()
                hebel = self.source.loc[i, "index_wert"] / abstand if abstand > 0 else 0
                self.hebel = min(hebel, 100)  # Cap bei Hebel von 100, um unrealistische Werte zu vermeiden
        
        

        def get_investment_value(self):
            return self.investment_value

        def update_investment_value(self, i):
            if i == self.i:
                self.investment_value = self.starting_investment

            if self.get_hebel() == 0:
                self.investment_value = 0
                return

            growth = 1 + self.source.loc[i, "index_growth"] * self.get_hebel()
            self.investment_value *= growth
        
        
        def get_gewinn(self):
            return self.gewinn
        
        def update_gewinn(self):
            self.gewinn = round(self.get_investment_value() - self.starting_investment, 2)