import duckdb
import pickle
import os
from functions.df_functions import get_index_map


def load_from_db():

    db_path = os.path.join('database', 'simulations.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    try:
        con = duckdb.connect(db_path)
        # Check if table exists
        if not con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='simulations'").fetchone():
            con.close()
            return None
        
        # Load data
        df = con.execute("SELECT * FROM simulations").fetchdf()
        results = {}
        for _, row in df.iterrows(): #"_" because index like 0,1,2,3 is not needed (trying some new mechanics)
            key = (row['index_name'], row['leverage'])
            results[key] = {
                'df_all_index': pickle.loads(row['df_all_index_pickle']),
                'df_investment': pickle.loads(row['df_investment_pickle']),
                'df_plot': pickle.loads(row['df_plot_pickle']),
                'df_table': pickle.loads(row['df_table_pickle']),
                'remaining_budget': row['remaining_budget'],
                'cumulative_value': row['cumulative_value'],
                'metrics': pickle.loads(row['metrics_pickle'])
            }
        
        # Check if all combinations exist
        index_map = get_index_map()
        expected_keys = {(index_name, leverage) for index_name in index_map.keys() for leverage in [3, 5, 10]}
        if set(results.keys()) != expected_keys:
            con.close()
            return None
        
        con.close()
        return results
    
    except Exception as error_message:
        print(f"Error loading from DB: {error_message}")
        return None


def store_to_db(results):
    
    db_path = os.path.join('database', 'simulations.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    con = duckdb.connect(db_path)
    con.execute("DROP TABLE IF EXISTS simulations")
    con.execute("CREATE TABLE simulations (index_name VARCHAR, leverage INTEGER, df_all_index_pickle BLOB, df_investment_pickle BLOB, df_plot_pickle BLOB, df_table_pickle BLOB, remaining_budget DOUBLE, cumulative_value DOUBLE, metrics_pickle BLOB)")
    for key, value in results.items():
        index_name, leverage = key
        con.execute("INSERT INTO simulations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", [
            index_name,
            leverage,
            pickle.dumps(value['df_all_index']),
            pickle.dumps(value['df_investment']),
            pickle.dumps(value['df_plot']),
            pickle.dumps(value['df_table']),
            value['remaining_budget'],
            value['cumulative_value'],
            pickle.dumps(value['metrics'])
        ])
    con.close()
