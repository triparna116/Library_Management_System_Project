import sqlite3

def create_database():
    conn = sqlite3.connect('library.db')
    cursor = conn.cursor()
    
    # --- 1. USERS Table ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            UserID TEXT PRIMARY KEY,
            Name TEXT NOT NULL,
            Password TEXT NOT NULL,
            IsAdmin INTEGER NOT NULL,
            IsActive INTEGER NOT NULL
        )
    """)
    
    # --- 2. MEMBERSHIPS Table ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memberships (
            MembershipID TEXT PRIMARY KEY,
            FirstName TEXT NOT NULL,
            LastName TEXT NOT NULL,
            ContactNumber TEXT NOT NULL,
            ContactAddress TEXT NOT NULL,
            AadharCardNo TEXT NOT NULL,
            StartDate TEXT NOT NULL,
            EndDate TEXT NOT NULL,
            Status TEXT NOT NULL,
            PendingFine REAL NOT NULL
        )
    """)
    
    # --- 3. ITEMS Table (Books/Movies) ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            SerialNo TEXT PRIMARY KEY,
            Name TEXT NOT NULL,
            AuthorName TEXT,
            Category TEXT,
            Type TEXT NOT NULL,
            Cost REAL,
            ProcurementDate TEXT,
            TotalCopies INTEGER NOT NULL,
            AvailableCopies INTEGER NOT NULL,
            CurrentStatus TEXT NOT NULL
        )
    """)
    
    # --- 4. TRANSACTIONS Table (Issues/Returns) ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            TransactionID INTEGER PRIMARY KEY AUTOINCREMENT,
            SerialNo TEXT NOT NULL,
            MembershipID TEXT NOT NULL,
            IssueDate TEXT NOT NULL,
            ReturnDate TEXT NOT NULL,
            ActualReturnDate TEXT,
            FineCalculated REAL DEFAULT 0.0,
            FinePaid INTEGER DEFAULT 0,
            Remarks TEXT
        )
    """)

    # Insert default users (adm/user)
    default_users = [
        ('adm', 'Admin User', 'adm', 1, 1),
        ('user', 'Normal User', 'user', 0, 1),
    ]
    
    for user_data in default_users:
        try:
            conn.execute("INSERT INTO users (UserID, Name, Password, IsAdmin, IsActive) VALUES (?, ?, ?, ?, ?)", user_data)
        except sqlite3.IntegrityError:
            pass 

    conn.commit()
    conn.close()

if __name__ == '__main__':
    create_database()
    print("Database 'library.db' and tables created successfully.")