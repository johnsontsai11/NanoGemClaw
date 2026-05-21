import psycopg2
import os
import time
import socket

def get_connection():
    """Create a connection to the PostgreSQL database using environment variables."""
    host = os.getenv("POSTGRES_HOST", "192.168.147.2")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    database = os.getenv("POSTGRES_DB", "stock_db")
    user = os.getenv("POSTGRES_USER", "ngc_postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")


    # Retry logic for database availability
    max_retries = 2
    for i in range(max_retries):
        try:
            conn = psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=user,
                password=password,
                connect_timeout=3
            )
            # Masked logging
            print(f"Successfully connected to postgres://{user}:****@{host}:{port}/{database}")
            return conn
        except Exception as e:
            if i < max_retries - 1:
                print(f"Database connection failed, retrying in 2 seconds... ({e})")
                time.sleep(2)
            else:
                raise e


def init_db():
    """Initialize the database schema and convert to TimescaleDB hypertable if needed."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create the daily table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tmf_daily (
            date        DATE PRIMARY KEY,
            price       DOUBLE PRECISION,
            inst_long   INTEGER,
            inst_short  INTEGER,
            total_oi    INTEGER,
            ratio       DOUBLE PRECISION,
            created_at  TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Check if hypertable extension exists and create hypertable
    try:
        cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'")
        if cursor.fetchone():
            # Check if it's already a hypertable
            cursor.execute("SELECT 1 FROM timescaledb_information.hyper_tables WHERE table_name = 'tmf_daily'")
            if not cursor.fetchone():
                print("Converting tmf_daily to TimescaleDB hypertable...")
                # We need to drop the primary key constraint or use it in partitioning
                # TimescaleDB requires the partitioning column (date) to be part of the primary key
                cursor.execute("SELECT create_hypertable('tmf_daily', 'date', if_not_exists => TRUE)")
    except Exception as e:
        print(f"Note: Could not enable TimescaleDB features (is the extension loaded?): {e}")

    conn.commit()
    cursor.close()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
