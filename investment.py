from numpy import floor

class investment:
        def __init__(self, source, i, selected_hebel, selected_budget, remaining_budget, inv_id):
            self.source = source
            self.i = i
            self.id = inv_id
            self.selected_hebel = selected_hebel
            self.selected_budget = selected_budget #kann reduziert werden
            self.remaining_budget = remaining_budget #am Ende anpassen und nicht immer übergeben werden. (wird ja erst beim investment verändert!)

            self.starting_date = self.source.loc[self.i, "date"]
            self.active = False
            self.closing_reason = None #False = Knockout, True = Sell
            self.starting_investment = 0.0
            self.active_investment = 0.0
            self.price_of_option = 0.0
            self.possible_amount_of_options = 0


        def start_investment(self):

            self.update_current_knockout_barrier(i=self.i) #setzt die Knockoutbarriere zum Startzeitpunkt

            abstand = self.source.loc[self.i, "index_wert"] - self.get_current_knockout_barrier()
            price_of_option = abstand * 0.01 #Bezugsverhältnis

            max_accessible_budget = self.selected_budget * 0.2
            actual_invested_budget = min(max_accessible_budget, self.remaining_budget)

            if actual_invested_budget < price_of_option:
                return
            
            self.active = True #setzt die Investition a   ls aktiv 

            possible_amount_of_options = floor(actual_invested_budget / price_of_option)
            self.active_investment = possible_amount_of_options * price_of_option
            self.starting_investment = self.active_investment #Für die späteren Renditeberechnung



        def reset_investment(self, type):
            self.active = False
            self.active_investment = None
            self.current_knockout_barrier = None

            if type == "sell":
                self.closing_reason = True
            elif type == "knockout":
                self.closing_reason = False


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


        def get_hebel(self, i):

            if i == self.i:
                return self.selected_hebel
            
            if i > self.i:
                abstand = self.source.loc[i, "index_wert"] - self.get_current_knockout_barrier()
                hebel = self.source.loc[i, "index_wert"] / abstand if abstand > 0 else 0
                return min(hebel, 100)  # Cap bei Hebel von 100, um unrealistische Werte zu vermeiden
            
            return 0
        
        
        def update_investment_value(self, i):
            if i == self.i:
                return self.active_investment

            hebel = self.get_hebel(i)
            if hebel == 0:
                self.active_investment = 0
                return 0

            growth = 1 + self.source.loc[i, "index_growth"] * hebel
            self.active_investment *= growth

            return self.active_investment
        
        
        def get_rendite(self, i):
            return round(self.active_investment - self.starting_investment, 3)