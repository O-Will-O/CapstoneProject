from flask import Flask, render_template, request, redirect, url_for, session, flash
from sqlalchemy import create_engine, text
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re

app = Flask(__name__)
app.secret_key = 'secret_key'



# connection string is in the format mysql://user:password@server/database
conn_str = "mysql://root:cyber241@localhost/CapstoneProject"
engine = create_engine(conn_str, echo=True)
conn = engine.connect()

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

ADMIN_USERNAME = "Admin"
ADMIN_PASSWORD = "AdminPass123"


@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['loggedin'] = True
            session['Username'] = "Admin"
            return redirect(url_for('admin_home'))

        account = conn.execute(text("SELECT * FROM users WHERE username = :username AND password = :password"),
                               {'username': username, 'password': password})
        user_data = account.fetchone()

        if user_data:
            session['loggedin'] = True
            session['Username'] = user_data[0]
            session["Name"] = f"{user_data[1]} {user_data[2]}"
            return redirect(url_for('index'))
        else:
            msg = 'Wrong username or password'

    return render_template('login.html', msg=msg)


@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('Username', None)
    session.pop('Name', None)
    session.pop('WaitingForApproval', None)
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
            for error in errorIn:
                flash(f'Invalid {error} format. Please check and try again.', 'error')
        elif Checkexist(username):
            flash('This Account Already Exists!', 'error')
        else:
            # Use a transaction to insert data safely
            with engine.begin() as conn:
                conn.execute(text(
                    "INSERT INTO to_be_reviewed (username, password, email, first_name, last_name, phone_number, address) "
                    "VALUES (:username, :password, :email, :firstname, :lastname, :phone, :address)"
                ), {
                    'username': username,
                    'password': password,
                    'email': email,
                    'firstname': firstname,
                    'lastname': lastname,
                    'phone': phone,
                    'address': address
                })

            session['loggedin'] = True
            session['Username'] = username
            session["Name"] = f"{firstname} {lastname}"
            session["WaitingForApproval"] = True
            return redirect(url_for('wait'))

    return render_template('signup.html', msg=msg)

@app.route("/waiting")
def wait():
    return render_template("waiting.html")


def CanAccess():
    username = session["Username"]
    if username == "Admin":
        return None
    if username != "Admin":
        return flash("Access Denied", "error"), redirect(url_for('index'))


@app.route('/admin_home')
def admin_home():
    if 'loggedin' in session and session['Username'] == "Admin":
        return render_template('admin_home.html', msg=session.get('msg'))
    return redirect(url_for('index')), flash("Access Denied", "error")


@app.route('/accountReview', methods=['GET', 'POST'])
def accountReview():
    if 'loggedin' in session and session['Username'] == "Admin":
        if request.method == 'GET':
            accounts = conn.execute(
                text('SELECT username, first_name, last_name, phone_number, email FROM to_be_reviewed;')).fetchall()
            return render_template("accountReview.html", accounts=accounts)

        elif request.method == 'POST':
            username = request.form['username']
            account = conn.execute(text('SELECT * FROM to_be_reviewed WHERE username = :username;'),
                                   {"username": username}).fetchone()

            if account:
                conn.execute(text(
                    'INSERT INTO users (username, password, email, first_name, last_name, phone_number, address) '
                    'VALUES (:username, :password, :email, :first_name, :last_name, :phone_number, :address);'),
                    {
                        'username': account[0], 'password': account[1], 'email': account[2],
                        'first_name': account[3], 'last_name': account[4],
                        'phone_number': account[5], 'address': account[6]
                    }
                )
                conn.execute(text('DELETE FROM to_be_reviewed WHERE username = :username;'), {'username': username})
                conn.commit()
                flash("Account approved successfully!", "success")

            return redirect(url_for('accountReview'))

    return redirect(url_for('login'))


if __name__ == "__main__":
    app.run(debug=True)