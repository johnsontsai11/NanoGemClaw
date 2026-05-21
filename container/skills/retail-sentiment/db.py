import psycopg2
from psycopg2 import pool
import os
import time
import socket

# Global connection pool
connection_pool = None

def init_pool():
    """Initialize connection pool (lazy initialization)"""
    global connection_pool
    if connection_pool is None:
        try:
            connection_pool = pool.SimpleConnectionPool(
                1, 5,  # min 1, max 5 connections
                host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
                port=int(os.getenv("POSTGRES_PORT", "5432")),
                database=os.getenv("POSTGRES_DB", "stock_db"),
                user=os.getenv("POSTGRES_USER", "ngc_postgres"),
                password=os.getenv("POSTGRES_PASSWORD", "!6WzrAiQYRwIJFQy"),
                connect_timeout=3
            )
        except Exception as e:
            print(f"Failed to create connection pool: {e}")
            raise

def get_connection():
    """Get a connection from the pool. Caller must call return_connection() when done."""
    if connection_pool is None:
        init_pool()

    max_retries = 2
    for i in range(max_retries):
        try:
            conn = connection_pool.getconn()
            if conn:
                return conn
        except Exception as e:
            if i < max_retries - 1:
                print(f"Pool connection failed, retrying in 2 seconds... ({e})")
                time.sleep(2)
            else:
                raise e

def return_connection(conn):
    """Return a connection to the pool"""
    if connection_pool and conn:
        connection_pool.putconn(conn)


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
    return_connection(conn)

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
