import sqlite3
import os

DB_NAME = "site.db"

def init_db():
    """Initialize the database with tables and sample data if empty."""
    if not os.path.exists(DB_NAME):
        print(f"Creating new database: {DB_NAME}")

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
             
        # Create tables if they don't exist
        c.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                unit TEXT,
                image_url TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS cart (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                product_id INTEGER,
                quantity INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)

        # Insert sample products if table is empty
        c.execute("SELECT COUNT(*) FROM products")
        if c.fetchone()[0] == 0:
            products = [
                ("Cassava", "Perfect for fufu, gari, and other dishes.", 1500, "bag", "cassava.jpg"),
                ("Plantains", "Sweet or savory, versatile for frying or boiling.", 750, "bunch", "plantain.jpg"),
                ("Country Rice", "The heart of every Liberian meal.", 2700, "25 kg bag", "rice.jpg")
            ]
            c.executemany(
                "INSERT INTO products (name, description, price, unit, image_url) VALUES (?, ?, ?, ?, ?)",
                products
            )
            conn.commit()
            print("Database initialized with sample products.")

def get_db_connection():
    """Return a new connection to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def migrate_users_table():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()

        # Step 1: Create a temporary users table with password column and UNIQUE email
        c.execute("""
            CREATE TABLE IF NOT EXISTS users_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL DEFAULT ''
            )
        """)

        # Step 2: Copy existing users into new table
        # For old users without password, we set it to empty string
        c.execute("""
            INSERT OR IGNORE INTO users_new (id, name, email)
            SELECT id, name, email FROM users
        """)

        # Step 3: Drop old users table
        c.execute("DROP TABLE users")

        # Step 4: Rename new table to users
        c.execute("ALTER TABLE users_new RENAME TO users")

        conn.commit()
        print("Users table migrated successfully!")

if __name__ == "__main__":
    migrate_users_table()