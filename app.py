from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify, render_template, g, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import os
import csv
import logging
from apple_id_checker import AppleIDChecker
import time
import sqlite3
from functools import wraps


# 创建一个 logger
logger = logging.getLogger(__name__)


app = Flask(__name__)

DATABASE = 'verification_results.db'


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row  # Return rows as dicts instead of tuples
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def init_db():
    with app.app_context():
        db = get_db()
        # Create table (if it doesn't exist already)
        db.execute('''
            CREATE TABLE IF NOT EXISTS verification (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                apple_id TEXT NOT NULL,
                password TEXT NOT NULL,
                verified BOOLEAN NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
        ''')
        db.commit()

@app.route('/create_user', methods=['POST'])
def create_user():
    username = request.form['username']
    password = request.form['password']
    hashed_password = generate_password_hash(password)

    db = get_db()
    try:
        db.execute('INSERT INTO user (username, password) VALUES (?, ?)', (username, hashed_password))
        db.commit()
    except sqlite3.IntegrityError:  # This will occur if the username is not unique
        return jsonify({'status': 'error', 'message': 'This username is already taken.'}), 400

    return jsonify({'status': 'success', 'message': 'User created successfully.'})


# Configure your secret key and upload folder
app.secret_key = 'your_secret_key'
# Make sure this path exists and is writeable
app.config['UPLOAD_FOLDER'] = 'uploadfile'

# Ensure the folder for uploads exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Allowed extension you want to allow for uploads
ALLOWED_EXTENSIONS = {'txt', 'csv'}

# Check if an extension is valid


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Login route


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db()
        user = db.execute(
            'SELECT * FROM user WHERE username = ?', (username,)).fetchone()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            # Or whatever the main page route is
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')

    return render_template('login.html')

# Logout route


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

# Decorator for protected routes


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Define the route for the main page


@app.route('/')
@login_required
def index():
    # The HTML file will be looked for in the 'templates' folder, so make sure 'index.html' is present there
    return render_template('index.html')

# Define the route for user verification


@app.route('/verify', methods=['POST'])
@login_required
def verify():
    verify_apple_id = AppleIDChecker().try_login
    # Simulate verification delay
    time.sleep(1)  # Sleep for 1 second to simulate real-time delay

    data = request.get_json()
    apple_id = data.get('apple_id')
    password = data.get('password')

    # This is a dummy verification process.
    # Replace this with your actual verification logic.
    # For example, to randomly simulate success or failure, you could do:
    verified = verify_apple_id(apple_id, password)
    # print('|||||||||||', verified)
    store_verified = verified.get('status')
    # After verification, insert result into database
    db = get_db()
    db.execute('''
        INSERT INTO verification (apple_id, password, verified)
        VALUES (?, ?, ?)
    ''', (apple_id, password, store_verified))
    db.commit()

    # Return a JSON response with the verification result
    return jsonify({
        "apple_id": apple_id,
        "verified": verified,
        "status": verified.get('status') if verified else "Not Verified"
    })

# Define the route for file upload and parsing


@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    # Check if the post request has the file part
    if 'file' not in request.files:
        return jsonify(status="error", message="No file part in the request"), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify(status="error", message="No selected file"), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Once the file is saved, parse it and return the content
        return jsonify(parse_file(file_path))

    return jsonify(status="error", message="File type not allowed"), 400

# Helper function to parse the uploaded file


def parse_file(filepath):
    results = []  # Initialize an empty list for results
    with open(filepath, 'r', encoding='utf-8') as file:
        # Ensure the delimiter matches the file format
        reader = csv.reader(file, delimiter=':')
        # Start enumeration at 1 for row numbers
        for row_number, row in enumerate(reader, start=1):
            if len(row) != 2:  # Check if the row has exactly two columns
                # Log an error or add an error message to the results indicating the problematic row
                logger.error(
                    f"Row {row_number} in the file does not have exactly two columns: {row}")
                results.append({"apple_id": "Error", "password": "Error",
                               "verified": "Row format error", "row_number": row_number})
                continue  # Skip further processing for this row

            # Otherwise, process the row normally
            apple_id, password = row
            verified = False  # Replace this with the actual verification once integrated
            # Add the processed data to the results list
            results.append({"apple_id": apple_id, "password": password,
                           "verified": verified, "row_number": row_number})

    return results


# Route for batch verification
@app.route('/batch-verify', methods=['POST'])
@login_required
def batch_verify():
    verify_apple_id = AppleIDChecker().try_login
    credentials_list = request.json
    results = []

    for credentials in credentials_list:
        apple_id = credentials.get('apple_id')
        password = credentials.get('password')
        # Verify the credentials (this should be replaced with actual verification logic)
        time.sleep(1)  # Add 1 second delay
        verified = verify_apple_id(apple_id, password)
        results.append(
            {"apple_id": apple_id, "password": password, "verified": verified})

    return jsonify(results)


@app.route('/results')
@login_required
def show_results():
    db = get_db()
    cur = db.execute('SELECT * FROM verification ORDER BY timestamp DESC')
    verification_results = cur.fetchall()
    return render_template('results.html', verification_results=verification_results)


if __name__ == '__main__':
    init_db()
    app.run(debug=True)  # Turn off debug in production environment
