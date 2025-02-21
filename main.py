from flask import Flask, render_template, request, redirect, url_for, session, flash
from sqlalchemy import create_engine, text
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re

app = Flask(__name__)
app.secret_key = 'secret_key'



# connection string is in the format mysql://user:password@server/database
conn_str = "mysql://root:Ilikegames05!@localhost/CapstoneProject"
engine = create_engine(conn_str, echo=True)
conn = engine.connect()


@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        account = conn.execute(text("SELECT * FROM users WHERE username = :username AND password = :password"),
                               request.form)
        user_data = account.fetchone()
        if not account:
            toBeR = conn.execute(text("Select username from to_be_reviewed where username = :username "),
                                 {'username': user_data[0]})
            toBeUse = toBeR.fetchone()
            if username == toBeUse[0] and password == toBeUse[6]:
                session['loggedin'] = True
                session['Username'] = toBeUse[0]
                session["Name"] = f"{toBeUse[1]} {toBeUse[2]}"
                session["WaitingForApproval"] = True
                return redirect(url_for('wait'))
        elif account:
            if username == user_data[0] == "Admin":
                session['loggedin'] = True
                session['Username'] = "Admin"
                return redirect(url_for('admin_home'))
            elif username == user_data[0] and password == user_data[6]:
                session['loggedin'] = True
                session['Username'] = user_data[0]
                session["Name"] = f"{user_data[1]} {user_data[2]}"
                msg = 'Login success!'
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
        ssn = request.form['SSN']
        phone = request.form['phone_number']
        address = request.form['address']

        yn, errorIn = checkinput(phone, ssn)
        if not yn:
            for error in errorIn:
                flash(f'Invalid {error} format. Please check and try again.', 'error')
        elif Checkexist(username):
            flash('This Account Already Exists!', 'error')
        else:
            conn.execute(text(
                "INSERT INTO to_be_reviewed (username, password, email, first_name, last_name, SSN, phone_number, address) "
                "VALUES (:username, :password, :email, :firstname, :lastname, :ssn, :phone, :address)"),
                {
                    'username': username,
                    'password': password,
                    'email': email,
                    'firstname': firstname,
                    'lastname': lastname,
                    'ssn': ssn,
                    'phone': phone,
                    'address': address
                })

            conn.commit()
            session['loggedin'] = True
            session['Username'] = username
            session["Name"] = f"{firstname} {lastname}"
            session["WaitingForApproval"] = True
            return redirect(url_for('waiting'))
        return render_template('signup.html', msg=msg)