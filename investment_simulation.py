import streamlit as st
import pandas as pd
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

    rows = [] #Zum unterscheiden der Reihen, der Investments
    investments_list = [] #Liste der Klassen von Investment
    investment_count = 0 #Zählt die Anzahl an Investment und wird für die Vergabe der inv.id verwendet
    cumulative_value = 0 #Kumulativer Wert aller Investments, um die Rendite und aktuelleb Stand zu berechnen

    for i in df[filter].index:

        if i%20 == 0: #Alle 20 Handelstage (ca. 1 Monat umgerechnet) wird das monatliche Budget erhöht
            remaining_budget += selected_budget

        if df.loc[i, "index_investpoint"]:
            
            investment_count += 1
            new_inv = Investment(source=df, #Erstellen eines neuen Investments
                            i=i,
                            selected_hebel=selected_hebel,
                            selected_budget=selected_budget,
                            remaining_budget=remaining_budget,
                            inv_id=investment_count) #ID des Investments == Invest_counter
            investments_list.append(new_inv) #Hinzufügen zu investments Liste
            new_inv.start_investment() #Startet das Investment
            if new_inv.active:
                remaining_budget -= new_inv.get_investment_value() #Abziehen des Investments vom Budget

        # Calculate cumulative value at this timestamp
        timestamp_cumulative_value = 0
        
        for inv in investments_list:

            if not inv.active: #Falls das Investment bereits inaktiv ist zu diesem Zeitpunkt
                continue

            inv.update_current_knockout_barrier(i=i) #Aktualisiert die Knockoutbarriere
            inv.update_investment_value(i=i) #Aktualisiert den aktuellen Wert des Investments
            inv.update_hebel(i=i) #Aktualisiert den Hebel des Investments
            inv.update_gewinn() #Aktualisiert die Rendite des Investments

            #Fall eines Knockouts, berechnet aus Hebel
            if  inv.get_hebel() == 0:
                inv.reset_investment(type="knockout")
                closing_date = df.loc[i, "date"] #Setzt das Endedatum auf den aktuellen Zeitpunkt
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

            #Fall eines Knockouts, berechnet aus aktuellem Wert des Investments
            if inv.get_investment_value() <= 0:
                inv.reset_investment(type="knockout")
                closing_date = df.loc[i, "date"] #Setzt das Endedatum auf den aktuellen Zeitpunkt
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

            #Fall eines regulären Verkaufs, weil der Hebel unter 1.5x gefallen ist
            if inv.get_hebel() <= 1.5:
                inv.reset_investment(type="sell")
                closing_date = df.loc[i, "date"] #Setzt das Endedatum auf den aktuellen Zeitpunkt
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

            # speichern der Werte in zuordbaren Reihen
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
    df_investment = pd.DataFrame(rows) #Dataframe aus den gesammelten Reihen der Investments

    return investments_list, remaining_budget, df_investment


