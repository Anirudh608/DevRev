from contextlib import _RedirectStream, redirect_stderr, redirect_stdout
from flask import Flask, render_template, request, redirect, g, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'
DATABASE = 'flights.db'

# Function to get a database connection
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.execute('PRAGMA foreign_keys = ON')  # Enable foreign key constraints
    return db

# Create the flights table if it doesn't exist
def create_flights_table():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS flights
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  destination TEXT NOT NULL,
                  source TEXT NOT NULL,
                  date TEXT NOT NULL,
                  price REAL NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                flight_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone INTEGER NOT NULL,
                FOREIGN KEY (flight_id) REFERENCES flights (id) ON DELETE CASCADE
                )''')
    # Create the 'users' table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )''')

    conn.commit()

# Add flights route
@app.route('/add_flights', methods=['GET', 'POST'])
def add_flights():
    if request.method == 'POST':
        source = request.form['source']
        destination = request.form['destination']
        date = request.form['date']
        price = request.form['price']

        conn = get_db()
        c = conn.cursor()

        c.execute('''INSERT INTO flights (source, destination, date, price) VALUES (?, ?, ?, ?)''',
                  (source, destination, date, price))
        conn.commit()

        message = "Flight added successfully"

        return render_template('flights_added.html')

    conn = get_db()
    c = conn.cursor()

    c.execute('''SELECT * FROM flights''')
    flights = c.fetchall()

    return render_template('add_flights.html', flights=flights)

# Initialize the database before the first request
@app.before_request
def before_request():
    create_flights_table()

# Close the database connection after each request
@app.teardown_request
def teardown_request(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Homepage route
@app.route('/')
def index():
    return render_template('index.html')

# Flight search route
@app.route('/search', methods=['POST'])
def search():
    destination = request.form['destination']
    source = request.form['source']
    date = request.form['date']

    conn = get_db()
    c = conn.cursor()

    c.execute('''SELECT * FROM flights WHERE destination=? AND source=? AND date=?''',
              (destination, source, date))
    results = c.fetchall()

    return render_template('search.html', results=results)

# Flight booking route
@app.route('/book/<int:flight_id>', methods=['GET', 'POST'])
def book(flight_id):
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']

        conn = get_db()
        c = conn.cursor()

        # Save the booking details to the database
        c.execute('''INSERT INTO bookings (flight_id, name, email, phone) VALUES (?, ?, ?, ?)''',
                  (flight_id, name, email, phone))
        conn.commit()

        return render_template('thankyou.html')

    conn = get_db()
    c = conn.cursor()

    c.execute('''SELECT * FROM flights WHERE id=?''', (flight_id,))
    flight = c.fetchone()

    return render_template('book.html', flight=flight)

# Book flights route
@app.route('/book_flights', methods=['GET', 'POST'])
def book_flights():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        flight_id = request.form['flight_id']

        conn = get_db()
        c = conn.cursor()

        c.execute('''INSERT INTO bookings (flight_id, name, email, phone) VALUES (?, ?, ?, ?)''',
                  (flight_id, name, email, phone))
        conn.commit()

        return render_template('thankyou.html')

    conn = get_db()
    c = conn.cursor()

    c.execute('''SELECT * FROM flights''')
    flights = c.fetchall()

    return render_template('book_flights.html', flights=flights)


# Remove flight route
@app.route('/remove_flight/<int:flight_id>', methods=['POST', 'GET'])
def remove_flight(flight_id):
    if request.method == 'POST':
        conn = get_db()
        c = conn.cursor()

        c.execute('DELETE FROM flights WHERE id = ?', (flight_id,))
        conn.commit()

        return render_template('flights_removed.html')
    else:
        return 'Method not allowed!'


# Bookings route
@app.route('/bookings')
def bookings():
    conn = get_db()
    c = conn.cursor()

    c.execute('''SELECT b.id, f.source, f.destination, f.date, f.price, b.name
                  FROM bookings b
                  JOIN flights f ON b.flight_id = f.id''')
    bookings = c.fetchall()

    return render_template('bookings.html', bookings=bookings)

# Clear bookings route
@app.route('/clear_bookings', methods=['POST'])
def clear_bookings():
    conn = get_db()
    c = conn.cursor()

    c.execute('DROP TABLE bookings')
    conn.commit()

    return redirect('/bookings')


# User login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        c = conn.cursor()

        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = c.fetchone()

        if user and user[2] == password:
            session['logged_in'] = True
            session['username'] = username
            return render_template('book_flights.html')
        else:
            return render_template('login.html', error='Invalid username or password')

    return render_template('login.html', error=None)

# User logout route
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# Example route that requires user authentication
@app.route('/profile')
def profile():
    if not session.get('logged_in'):
        return redirect('/login')
    return render_template('profile.html', username=session.get('username'))


# Sign-up route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        c = conn.cursor()

        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            session['logged_in'] = True
            session['username'] = username
            return render_template('login.html')
        except sqlite3.IntegrityError:
            error = 'Username already exists. Please choose a different username.'
            return render_template('signup.html', error=error)

    return render_template('signup.html', error=None)

# User ID and password table route
@app.route('/user_table')
def user_table():
    conn = get_db()
    c = conn.cursor()

    c.execute('SELECT id, username, password FROM users')
    user_data = c.fetchall()

    return render_template('user_table.html', user_data=user_data)

# Admin login route
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == 'admin' and password == 'DevRev@12':
            session['admin_logged_in'] = True
            return redirect('/admin/dashboard')
        else:
            return render_template('admin_login.html', error='Invalid username or password')

    return render_template('admin_login.html', error=None)

# Admin dashboard route
@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect('/admin/login')
    return render_template('admin_dashboard.html')

app.use_x_sendfile = True


if __name__ == '__main__':
    
    app.run(debug=True)
    create_flights_table()
   
