from sqlalchemy import create_engine, text
import os

# Use localhost because we run this script from host, mapping to docker port? 
# Wait, docker port 5432 is exposed.
DATABASE_URL = "postgresql://odoo:odoo@localhost:5432/bff"

def reset_db():
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE;"))
            conn.execute(text("CREATE SCHEMA public;"))
            conn.commit()
        print("Database reset successfully.")
    except Exception as e:
        print(f"Error resetting DB: {e}")

if __name__ == "__main__":
    reset_db()
