from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from sqlalchemy import create_engine, text
import re
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'secret_key'

# Database connection string
conn_str = "mysql://root:Ilikegames05!@localhost/CapstoneProject"
engine = create_engine(conn_str, echo=True)
conn = engine.connect()

# Admin credentials
ADMIN_USERNAME = "Admin"
ADMIN_PASSWORD = "AdminPass123"



from sqlalchemy import text

# Prefix-to-table/column map
ID_MAP = {
    'U': ('Users', 'UserID'),
    'C': ('Customers', 'CustomerID'),
    'P': ('Products', 'ProductID'),
    'D': ('Discount_info', 'DiscountID'),
    'COMP': ('Complaints', 'ComplaintID'),
    'O': ('Orders', 'OrderID')
}

def get_next_custom_id(prefix, conn):
    if prefix not in ID_MAP:
        raise ValueError(f"Unknown prefix '{prefix}'")

    table, column = ID_MAP[prefix]

    if prefix == 'U':
        # Integer auto-increment; return next integer
        result = conn.execute(text(f"SELECT MAX({column}) as max_id FROM {table}")).fetchone()
        return (result.max_id or 0) + 1

    elif prefix == 'COMP':
        query = text(f"""
            SELECT {column} FROM {table}
            WHERE {column} LIKE :prefix
            ORDER BY {column} DESC LIMIT 1
        """)
        result = conn.execute(query, {'prefix': f'{prefix}%'}).fetchone()
        if result:
            num = int(result[0].replace(prefix, '')) + 1
        else:
            num = 1
        return f"{prefix}{str(num).zfill(3)}"

    else:
        query = text(f"""
            SELECT {column} FROM {table}
            WHERE {column} LIKE :prefix
            ORDER BY {column} DESC LIMIT 1
        """)
        result = conn.execute(query, {'prefix': f'{prefix}%'})
        row = result.fetchone()
        if row:
            num = int(row[0][len(prefix):]) + 1
        else:
            num = 1
        return f"{prefix}{str(num).zfill(3)}"


def checkinput(phone):
    phone_pattern = r'^\d{10}$'
    yn = bool(re.match(phone_pattern, phone))
    errorIn = ["Phone"] if not yn else []
    return yn, errorIn

def Checkexist(username):
    account = conn.execute(text("SELECT username FROM users WHERE username = :username"), {'username': username})
    return account.fetchone() is not None


def checkinput(phone):

    phone_pattern = r'^\d{10}$'
    yn = True
    errorIn = []

    if not re.match(phone_pattern, phone):
        yn = False
        errorIn.append("Phone")

    return yn, errorIn


def Checkexist(username):
     username = str(username)
     account = conn.execute(text("SELECT username FROM users WHERE username = :username"), {'username': username})
     result = account.fetchone()
     if result:
         return True
     else:
        return False

@app.route("/")
def index():
    if 'loggedin' in session and session['Username'] != "Admin":
        return render_template("index.html")
    elif 'loggedin' in session and session['Username'] == "Admin":
        return redirect(url_for('admin_home'))
    else:
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['loggedin'] = True
            session['Username'] = "Admin"
            return redirect(url_for('admin_home'))

        account = conn.execute(text("SELECT * FROM users WHERE username = :username AND password = :password"),
                               {'username': username, 'password': password}).fetchone()

        if account:
            session['loggedin'] = True
            session['Username'] = account[0]
            session["Name"] = f"{account[1]} {account[2]}"
            return redirect(url_for('index'))
        else:
            msg = 'Wrong username or password'

    return render_template('login.html', msg=msg)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        firstname = request.form['first_name']
        lastname = request.form['last_name']
        phone = request.form['phone_number']
        address = request.form['address']

        yn, errorIn = checkinput(phone)
        if not yn:
            flash(f'Invalid {errorIn[0]} format. Please check and try again.', 'error')
        elif Checkexist(username):
            flash('This Account Already Exists!', 'error')
        else:
            with engine.begin() as conn:
                conn.execute(text(
                    "INSERT INTO to_be_reviewed (username, password, email, first_name, last_name, phone_number, address) "
                    "VALUES (:username, :password, :email, :firstname, :lastname, :phone, :address)"),
                    {'username': username, 'password': password, 'email': email, 'firstname': firstname,
                     'lastname': lastname, 'phone': phone, 'address': address})

            session['loggedin'] = True
            session['Username'] = username
            session["Name"] = f"{firstname} {lastname}"
            session["WaitingForApproval"] = True
            return redirect(url_for('wait'))

    return render_template('signup.html', msg=msg)

@app.route("/waiting")
def wait():
    return render_template("waiting.html")

@app.route('/admin_home')
def admin_home():
    if 'loggedin' in session and session['Username'] == "Admin":
        accounts = conn.execute(text('SELECT username, first_name, last_name, email, phone_number FROM to_be_reviewed')).fetchall()
        return render_template('admin_home.html', accounts=accounts)
    flash("Access Denied", "error")
    return redirect(url_for('index'))


@app.route('/approve_user', methods=['POST'])
def approve_user():
    if 'loggedin' in session and session['Username'] == "Admin":
        username = request.form['username']
        account = conn.execute(text('SELECT * FROM to_be_reviewed WHERE username = :username'),
                               {'username': username}).fetchone()

        if account:
            conn.execute(text(
                'INSERT INTO users (username, password, email, first_name, last_name, phone_number, address) '
                'VALUES (:username, :password, :email, :first_name, :last_name, :phone_number, :address)'),
                {'username': account[0], 'password': account[1], 'email': account[2],
                 'first_name': account[3], 'last_name': account[4], 'phone_number': account[5], 'address': account[6]})

            conn.execute(text('DELETE FROM to_be_reviewed WHERE username = :username'), {'username': username})
            conn.commit()
            flash("Account approved successfully!", "success")

        return redirect(url_for('admin_home'))

    flash("Access Denied", "error")
    return redirect(url_for('login'))


@app.route('/reject_user', methods=['POST'])
def reject_user():
    if 'loggedin' in session and session['Username'] == "Admin":
        username = request.form['username']
        conn.execute(text('DELETE FROM to_be_reviewed WHERE username = :username'), {'username': username})
        conn.commit()
        flash("Account rejected and removed.", "info")
        return redirect(url_for('admin_home'))

    flash("Access Denied", "error")
    return redirect(url_for('login'))


@app.route('/game', methods=['GET', 'POST'])
def gamePage():
    if request.method == 'GET':
        return render_template("discount_game_page.html")
    
    if request.method == 'POST':
        session['CustomerID'] = "C001" #REMOVE AFTER GETTING ALL LOGIN STUFF CORRECT
        if 'CustomerID' not in session:
            return jsonify({'status': 'error', 'message': 'Customer not logged in'}), 401
            
        customer_id = session['CustomerID']
        score = int(request.form.get('score', 0))
        
        # Calculate discount amount ((score/1000)/2)%
        discount_amount = (score / 100000) / 2
        
        # Get current date and 6 months later
        date_started = datetime.now()
        time_available = date_started + timedelta(days=180)
        
        discount_id = get_next_custom_id("D", conn)
        print("TESTING THE NEW FUNCTION", discount_id)

        print("THIS IS FOR TESTING PORPOSES", discount_id, discount_amount, date_started, time_available)
        conn.execute(text("""
                    INSERT INTO Discount_info 
                    (CustomerID, DiscountID, Discount_amount, Date_started, Time_available) 
                    VALUES (:customer_id, :discount_id, :discount_amount, :date_started, :time_available)
                """), {
                    'customer_id': customer_id,
                    'discount_id' : discount_id,
                    'discount_amount': discount_amount,
                    'date_started': date_started,
                    'time_available': time_available
                })
        conn.commit()
        return redirect(url_for('index'))



if __name__ == "__main__":
    app.run(debug=True)
