import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, g
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your_super_secret_key'

# --- Database Connection Management ---
def get_db_connection():
    if 'db' not in g:
        g.db = sqlite3.connect('library.db')
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

import setup_db
setup_db.create_database()

# --- Helper Functions ---
def generate_id(prefix, conn):
    today_str = datetime.now().strftime('%Y%m%d')
    
    if prefix == 'M':
        last_id = conn.execute("SELECT MembershipID FROM memberships WHERE MembershipID LIKE ? ORDER BY MembershipID DESC LIMIT 1", (prefix + today_str + '%',)).fetchone()
    elif prefix in ('B', 'M'):
        last_id = conn.execute("SELECT SerialNo FROM items WHERE SerialNo LIKE ? ORDER BY SerialNo DESC LIMIT 1", (prefix + today_str + '%',)).fetchone()
    else:
        return prefix + today_str + '001'
    
    if last_id:
        last_counter = int(last_id[0][-3:])
        new_counter = last_counter + 1
    else:
        new_counter = 1
        
    return f"{prefix}{today_str}{new_counter:03d}"

# --- Route 1: Login Page ---
@app.route('/', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('admin_home') if session.get('is_admin') == 1 else url_for('user_home'))
        
    error = None
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute(
            'SELECT * FROM users WHERE UserID = ? AND Password = ? AND IsActive = 1', 
            (user_id, password)
        ).fetchone()
        
        if user:
            session['logged_in'] = True
            session['user_id'] = user['UserID']
            session['is_admin'] = user['IsAdmin']
            
            return redirect(url_for('admin_home') if user['IsAdmin'] == 1 else url_for('user_home'))
        else:
            error = 'Invalid Credentials or User Inactive.'
            
    return render_template('login.html', error=error)

# --- Route 2: Admin Home Page ---
@app.route('/admin_home')
def admin_home():
    if not session.get('logged_in') or session.get('is_admin') != 1:
        return redirect(url_for('login'))
    return render_template('admin_home.html')

# --- Route 3: User Home Page ---
@app.route('/user_home')
def user_home():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('user_home.html')

# --- Route 4: Logout ---
@app.route('/logout')
def logout():
    session.clear()
    return render_template('login.html', message='You have successfully logged out.')

# --- Route 5: Add Membership ---
@app.route('/add_membership', methods=['GET', 'POST'])
def add_membership():
    if not session.get('logged_in') or session.get('is_admin') != 1:
        return redirect(url_for('login'))
        
    error = None
    success = None
    
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        contact_number = request.form['contact_number']
        contact_address = request.form['contact_address']
        aadhar_card_no = request.form['aadhar_card_no']
        start_date_str = request.form['start_date']
        membership_duration = request.form['membership_duration']
        
        if not all([first_name, last_name, contact_number, contact_address, aadhar_card_no, start_date_str, membership_duration]):
            error = "Error: All fields are mandatory."
            return render_template('add_membership.html', error=error)
            
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            
            if membership_duration == '6_months':
                end_date = start_date + timedelta(days=6*30) 
            elif membership_duration == '1_year':
                end_date = start_date + timedelta(days=365)
            elif membership_duration == '2_years':
                end_date = start_date + timedelta(days=2*365)

            end_date_str = end_date.strftime('%Y-%m-%d')
            
            conn = get_db_connection()
            membership_id = generate_id('M', conn)
            
            conn.execute(
                """
                INSERT INTO memberships 
                (MembershipID, FirstName, LastName, ContactNumber, ContactAddress, AadharCardNo, StartDate, EndDate, Status, PendingFine) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (membership_id, first_name, last_name, contact_number, contact_address, aadhar_card_no, start_date_str, end_date_str, 'Active', 0.0)
            )
            conn.commit()
            conn.close()
            
            success = f"New Membership created successfully! ID: {membership_id}"
            
        except ValueError:
            error = "Error: Invalid date format."
        except sqlite3.Error as e:
            error = f"Database Error: Could not add membership. {e}"

    return render_template('add_membership.html', error=error, success=success, current_date=datetime.now().strftime('%Y-%m-%d'))

# --- Route 6: Add Book/Movie ---
@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    if not session.get('logged_in') or session.get('is_admin') != 1:
        return redirect(url_for('login'))
        
    error = None
    success = None
    
    if request.method == 'POST':
        item_type = request.form.get('item_type', 'Book')
        name = request.form['name']
        author_director = request.form['author_director']
        category = request.form['category']
        cost = request.form['cost']
        procurement_date = request.form['procurement_date']
        quantity = request.form.get('quantity', 1) 
        
        if not all([name, author_director, category, cost, procurement_date, quantity]):
            error = "Error: All fields are mandatory."
            return render_template('add_item.html', error=error)
            
        try:
            quantity = int(quantity)
            cost = float(cost)
            
            conn = get_db_connection()
            prefix = 'B' if item_type == 'Book' else 'M'
            serial_no = generate_id(prefix, conn)
            
            conn.execute(
                """
                INSERT INTO items 
                (SerialNo, Name, AuthorName, Category, Type, Cost, ProcurementDate, TotalCopies, AvailableCopies, CurrentStatus) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (serial_no, name, author_director, category, item_type, cost, procurement_date, quantity, quantity, 'Available')
            )
            conn.commit()
            conn.close()
            
            success = f"New {item_type} added successfully! Serial No: {serial_no}"
            
        except ValueError:
            error = "Error: Invalid number format for Cost or Quantity."
        except sqlite3.Error as e:
            error = f"Database Error: Could not add item. {e}"

    return render_template('add_item.html', error=error, success=success, current_date=datetime.now().strftime('%Y-%m-%d'))

# --- Route 7: User Management ---
@app.route('/user_management', methods=['GET', 'POST'])
def user_management():
    if not session.get('logged_in') or session.get('is_admin') != 1:
        return redirect(url_for('login'))
    
    error = None
    success = None
    
    if request.method == 'POST':
        user_id = request.form['user_id']
        name = request.form['name']
        password = request.form['password']
        is_active = 1 if 'is_active' in request.form else 0
        is_admin = 1 if 'is_admin' in request.form else 0
        
        if not all([user_id, name, password]):
            error = "Error: User ID, Name, and Password are mandatory fields."
            return render_template('user_management.html', error=error)
            
        try:
            conn = get_db_connection()
            
            existing_user = conn.execute('SELECT UserID FROM users WHERE UserID = ?', (user_id,)).fetchone()
            if existing_user:
                 error = f"Error: User ID '{user_id}' already exists."
                 return render_template('user_management.html', error=error)
            
            conn.execute(
                """
                INSERT INTO users 
                (UserID, Name, Password, IsAdmin, IsActive) 
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, name, password, is_admin, is_active)
            )
            conn.commit()
            
            role = "Admin" if is_admin == 1 else "Normal User"
            status = "Active" if is_active == 1 else "Inactive"
            success = f"New user '{name}' created successfully! Role: {role}, Status: {status}."
            return render_template('user_management.html', success=success, active_tab='new') 
            
        except sqlite3.Error as e:
            error = f"Database Error: Could not add user. {e}"
            return render_template('user_management.html', error=error)

    return render_template('user_management.html', active_tab='new')

# --- Route 8: Book Availability ---
@app.route('/book_availability', methods=['GET', 'POST'])
def book_availability():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    error = None
    
    try:
        conn = get_db_connection()
        item_names = [row['Name'] for row in conn.execute('SELECT DISTINCT Name FROM items').fetchall()]
        item_authors = [row['AuthorName'] for row in conn.execute('SELECT DISTINCT AuthorName FROM items').fetchall()]
    except sqlite3.Error as e:
        error = f"Database Error: Could not retrieve item lists. {e}"
        item_names = []
        item_authors = []

    if request.method == 'POST':
        book_name = request.form['book_name'].strip()
        author_name = request.form['author_name'].strip()
        
        if not book_name and not author_name:
            error = "Error: Enter at least Book Name or Author Name."
            return render_template('book_availability.html', error=error, item_names=item_names, item_authors=item_authors)
            
        return redirect(url_for('search_results', name=book_name, author=author_name))
        
    return render_template('book_availability.html', error=error, item_names=item_names, item_authors=item_authors)

# --- Route 9: Search Results ---
@app.route('/search_results', methods=['GET'])
def search_results():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    name_query = request.args.get('name', '')
    author_query = request.args.get('author', '')
    
    return f"""
    <h1>Search Results (Coming Soon)</h1>
    <p><b>Book Name:</b> {name_query}</p>
    <p><b>Author:</b> {author_query}</p>
    <a href='{url_for('book_availability')}'>Back</a>
    """

# --- Route 12: Return Item ---
@app.route('/return_item', methods=['GET', 'POST'])
def return_item():
    if not session.get('logged_in') or session.get('is_admin') != 1:
        return redirect(url_for('login'))

    conn = get_db_connection()
    current_date = datetime.now().strftime('%Y-%m-%d')
    FINE_RATE_PER_DAY = 5.0 
    
    error = None
    success = None
    fine_calculated = None
    
    membership_id_form = ""
    serial_no_form = ""

    if request.method == 'POST':
        serial_no = request.form['serial_no'].strip()
        membership_id = request.form['membership_id'].strip()
        return_date_actual_str = request.form['return_date_actual']
        action = request.form['action']
        
        membership_id_form = membership_id
        serial_no_form = serial_no
        
        issue = conn.execute("""
            SELECT id, ReturnDateDue 
            FROM issues 
            WHERE SerialNo = ? AND MembershipID = ? AND Status = 'Active'
        """, (serial_no, membership_id)).fetchone()

        if not issue:
            error = "Error: No active issue found."
            return render_template('return_item.html', current_date=current_date, error=error, membership_id_form=membership_id_form, serial_no_form=serial_no_form)

        issue_id = issue['id']
        return_date_due_str = issue['ReturnDateDue']
        
        try:
            actual_dt = datetime.strptime(return_date_actual_str, '%Y-%m-%d')
            due_dt = datetime.strptime(return_date_due_str, '%Y-%m-%d')
            
            overdue_days = max(0, (actual_dt - due_dt).days)
            calculated_fine = overdue_days * FINE_RATE_PER_DAY
            fine_calculated = calculated_fine
            
            if action == 'check':
                if calculated_fine > 0:
                    success = f"Item is {overdue_days} days overdue."
                else:
                    fine_calculated = 0.0
                    success = "Item is on time."
                
            elif action == 'return':
                try:
                    conn.execute("""
                        UPDATE issues 
                        SET ReturnDateActual = ?, FineAmount = ?, FinePaid = 0.0, Status = 'Returned'
                        WHERE id = ?
                    """, (return_date_actual_str, calculated_fine, issue_id))
                    
                    conn.execute("UPDATE items SET AvailableCopies = AvailableCopies + 1 WHERE SerialNo = ?", (serial_no,))
                    
                    conn.execute("UPDATE memberships SET PendingFine = PendingFine + ? WHERE MembershipID = ?", (calculated_fine, membership_id))
                    
                    conn.commit()
                    
                    if calculated_fine > 0:
                        success = f"Returned! Fine: ₹{calculated_fine:.2f}"
                    else:
                        success = "Returned successfully."
                    
                    membership_id_form = ""
                    serial_no_form = ""
                    fine_calculated = None
                    
                except sqlite3.Error as e:
                    conn.rollback()
                    error = f"Database Error: {e}"
                    fine_calculated = calculated_fine
                    
        except ValueError:
            error = "Invalid date format."
            fine_calculated = fine_calculated

    conn.close()
    
    return render_template('return_item.html', 
                           current_date=current_date, 
                           error=error, 
                           success=success,
                           fine_calculated=fine_calculated,
                           membership_id_form=membership_id_form, 
                           serial_no_form=serial_no_form)

# --- Run ---
if __name__== '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)