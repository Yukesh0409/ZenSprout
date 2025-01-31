import pandas as pd
from sqlalchemy import create_engine
from app import app, db  # Import your Flask app and SQLAlchemy instance

DATABASE_URI = 'sqlite:///instance/zensprout.db'

engine = create_engine(DATABASE_URI)
def load_table_to_dataframe(table_name):
    query = f"SELECT * FROM {table_name};"
    df = pd.read_sql(query, engine)
    return df

tables = ['user', 'session']

for table in tables:
    print(f"\nContents of table '{table}':")
    df = load_table_to_dataframe(table)
    display(df)

    
