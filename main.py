from flask import Flask, render_template, request, redirect, url_for, session, flash
from sqlalchemy import create_engine, text
import re

app = Flask(__name__)
app.secret_key = 'secret_key'

# Database connection string
conn_str = "mysql://root:cyber241@localhost/CapstoneProject"
engine = create_engine(conn_str, echo=True)
conn = engine.connect()

# Admin credentials
ADMIN_USERNAME = "Admin"
ADMIN_PASSWORD = "AdminPass123"

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



if __name__ == "__main__":
    app.run(debug=True)
