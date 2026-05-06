import pandas as pd
from pathlib import Path
from functions.yfinance_loader import download


def get_index_map(folder="index_data"):
    index_map = {}

    if not any(Path(folder).glob("*.json")):
        print(f"No JSON files found in {folder}, downloading data...")
        download()
    
    #New Data should only be added when data is being refreshed

    for file in Path(folder).glob("*.json"):
        # Use filename (without extension) as default name
        name = file.stem
        
        name = name.replace("^", "")  # remove ^ if present
        
        index_map[name] = str(file)
    
    return index_map



def load_df(file_path):

    try:
        df = pd.read_json(file_path, orient="index")
        df.index = pd.to_datetime(df.index)
        df.columns = ["index_value"]
        df.index.name = "date"
        return df.reset_index()

    except Exception as error_message:
        print(f"Error loading JSON: {error_message}")
        return None



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

