import duckdb
import pandas as pd
import pickle
import os


def load_from_db():
    db_path = os.path.join("database", "simulations.db")
    if not os.path.exists(db_path):
        return {}
    con = duckdb.connect(db_path)

    try:
        df = con.execute("SELECT * FROM simulations").fetchdf()
        results = {}
        for _, row in df.iterrows():

            key = (row["index_name"], row["leverage"])

            results[key] = { 
                "df_all_index": pd.read_parquet(row["df_all_index_path"]),
                "df_investment": pd.read_parquet(row["df_investment_path"]),
                "df_table": pd.read_parquet(row["df_table_path"]),
                "remaining_budget": row["remaining_budget"],
                "cumulative_value": row["cumulative_value"],
                "metrics": pickle.loads(row["metrics_pickle"]),
                "df_plot_filtered": pd.read_parquet(row["df_plot_filtered_path"])
            }
        return results
    
    except Exception as e:
        print(f"Error loading DB: {e}")
        return {}
    
    finally:
        con.close()


def store_to_db(results):
    db_path = os.path.join("database", "simulations.db")
    parquet_dir = os.path.join("database", "parquet")
    os.makedirs(parquet_dir, exist_ok=True)
    con = duckdb.connect(db_path)

    con.execute("""
        CREATE OR REPLACE TABLE simulations (
            index_name VARCHAR,
            leverage INTEGER,

            df_all_index_path VARCHAR,
            df_investment_path VARCHAR,
            df_table_path VARCHAR,
            df_plot_filtered_path VARCHAR,
                
            remaining_budget DOUBLE,
            cumulative_value DOUBLE,
            metrics_pickle BLOB
        )
    """)

    for (index_name, leverage), value in results.items():
        paths = {}
        for name in [
            "df_all_index",
            "df_investment",
            "df_table",
            "df_plot_filtered"
        ]:
            
            path = os.path.join(
                parquet_dir,
                f"{index_name}_{leverage}_{name}.parquet"
            )
            value[name].to_parquet(
                path,
                compression="zstd",
                index=False
            )
            paths[name] = path

        con.execute("INSERT INTO simulations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", [
            index_name,
            leverage,
            paths["df_all_index"],
            paths["df_investment"],
            paths["df_table"],
            paths["df_plot_filtered"],
            value["remaining_budget"],
            value["cumulative_value"],
            pickle.dumps(value["metrics"]) #pickle because metrics are not a time-series
        ])
    con.close()