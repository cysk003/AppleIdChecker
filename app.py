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
import pandas as pd
from flask import Response


# 创建一个 logger
logger = logging.getLogger(__name__)

app = Flask(__name__)
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


DATABASE = 'verification_results.db'


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row  # Return rows as dicts instead of tuples
    return db


#
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


# Decorator for protected routes
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin', False):
            flash('Admin access required')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def init_db():
    with app.app_context():
        db = get_db()
        # Create table (if it doesn't exist already)
        db.execute('''
            CREATE TABLE IF NOT EXISTS verification (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                logged_in_user TEXT NOT NULL,
                apple_id TEXT NOT NULL,
                password TEXT NOT NULL,
                verified TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                verification_limit INTEGER DEFAULT 10,
                verification_count INTEGER DEFAULT 0,
                is_admin BOOLEAN DEFAULT 0
            )
        ''')
        db.commit()


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
            # Store username in session instead of or along with user_id
            session['username'] = username  # store username here
            session['user_id'] = user['id']
            session['is_admin'] = user['is_admin']
            # Or whatever the main page route is
            return redirect(url_for('index'))
        else:
            flash('用户名或密码错误！')

    return render_template('login.html')

# Logout route


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('is_admin', None)
    return redirect(url_for('login'))


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
    store_verified = verified.get('status')

    # 获取当前登录用户的用户名
    user_id = session.get('user_id')
    db = get_db()
    user_row = db.execute(
        'SELECT username FROM user WHERE id = ?', (user_id,)).fetchone()
    logged_in_user = user_row['username'] if user_row else None

    # Get the current user's verification count and limit
    user_verification = db.execute(
        'SELECT verification_count, verification_limit FROM user WHERE id = ?',
        (session['user_id'],)
    ).fetchone()

    if user_verification['verification_count'] >= user_verification['verification_limit']:
        return jsonify({'status': 'error', 'message': '你的检测次数额度已用完，联系管理员。'}), 403

    if logged_in_user:
        # 检查是否存在相同记录
        existing_record = db.execute(
            'SELECT id FROM verification WHERE logged_in_user = ? AND apple_id = ? AND password = ?',
            (logged_in_user, apple_id, password)
        ).fetchone()

        if existing_record:  # 如果记录存在，更新时间戳
            db.execute(
                'UPDATE verification SET timestamp = CURRENT_TIMESTAMP WHERE id = ?',
                (existing_record['id'],)
            )
        else:  # 如果不存在，插入新记录
            db.execute(
                'INSERT INTO verification (logged_in_user, apple_id, password, verified) VALUES (?, ?, ?, ?)',
                (logged_in_user, apple_id, password, store_verified)
            )
        # Increment the verification count
        db.execute(
            'UPDATE user SET verification_count = verification_count + 1 WHERE id = ?',
            (session['user_id'],)
        )
        db.commit()
    else:
        # If the session does not have a username, return an error response
        return jsonify({"status": "error", "message": "User is not logged in."}), 403

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

# def parse_file(filepath):
#     results = []  # Initialize an empty list for results
#     with open(filepath, 'r', encoding='utf-8') as file:
#         # Ensure the delimiter matches the file format
#         reader = csv.reader(file, delimiter=':')
#         # Start enumeration at 1 for row numbers
#         for row_number, row in enumerate(reader, start=1):
#             if len(row) != 2:  # Check if the row has exactly two columns
#                 # Log an error or add an error message to the results indicating the problematic row
#                 logger.error(
#                     f"Row {row_number} in the file does not have exactly two columns: {row}")
#                 results.append({"apple_id": "Error", "password": "Error",
#                                 "verified": "Row format error", "row_number": row_number})
#                 continue  # Skip further processing for this row

#             # Otherwise, process the row normally
#             apple_id, password = row
#             verified = False  # Replace this with the actual verification once integrated
#             # Add the processed data to the results list
#             results.append({"apple_id": apple_id, "password": password,
#                             "verified": verified, "row_number": row_number})

#     return results

def parse_file(filepath):
    results = []  # Initialize an empty list for results
    with open(filepath, 'r', encoding='utf-8') as file:
        # Start enumeration at 1 for row numbers
        for row_number, line in enumerate(file, start=1):
            row = line.strip().split('----')  # Split the line using the '----' delimiter
            if len(row) != 2:  # Check if the split line has exactly two parts
                # Log an error or add an error message to the results indicating the problematic row
                logger.error(
                    f"Row {row_number} in the file does not have exactly two parts: {line}")
                results.append({"apple_id": "Error", "password": "Error",
                                "verified": "Row format error", "row_number": row_number})
                continue  # Skip further processing for this row

            apple_id, password = row  # Unpack the split line into apple_id and password variables
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
        # time.sleep(1)  # Add 1 second delay
        verified = verify_apple_id(apple_id, password)
        results.append(
            {"apple_id": apple_id, "password": password, "verified": verified})

    return jsonify(results)


@app.route('/my-verification-results')
@login_required
def my_verification_results():
    user_id = session.get('user_id')
    db = get_db()
    user_row = db.execute(
        'SELECT username FROM user WHERE id = ?', (user_id,)).fetchone()
    logged_in_user = user_row['username'] if user_row else None

    if logged_in_user:
        cur = db.execute(
            'SELECT * FROM verification WHERE logged_in_user = ? ORDER BY timestamp DESC', (logged_in_user,))
        verification_results = cur.fetchall()
        return render_template('my_verification_results.html', verification_results=verification_results)
    else:
        # Handle the case where the user information is not found or user is not logged in
        flash('You need to be logged in to view this page.')
        return redirect(url_for('login'))


@app.route('/update_limit', methods=['POST'])
# @login_required
def update_limit():
    # if not is_admin():  # You need to implement is_admin check according to your app logic
    #     return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    data = request.get_json()
    user_id = data.get('user_id')
    new_limit = data.get('new_limit')

    db = get_db()
    db.execute(
        'UPDATE user SET verification_limit = ? WHERE id = ?',
        (new_limit, user_id)
    )
    db.commit()

    return jsonify({'status': 'success', 'message': 'Limit updated successfully.'})


@app.route('/disclaimer')
def disclaimer():
    return render_template('disclaimer.html')


@app.route('/admin', methods=['GET'])
@admin_required
def admin():
    db = get_db()
    users = db.execute(
        'SELECT id, username, verification_limit, verification_count, is_admin FROM user').fetchall()
    return render_template('admin.html', users=users)


@app.route('/admin/create_user', methods=['POST'])
@admin_required
def create_user():
    username = request.form['username']
    password = request.form['password']
    verification_limit = request.form['verification_limit']
    hashed_password = generate_password_hash(password)

    db = get_db()
    try:
        db.execute('INSERT INTO user (username, password, verification_limit) VALUES (?, ?, ?)',
                   (username, hashed_password, verification_limit))
        db.commit()
    except sqlite3.IntegrityError:
        flash('Username already exists.')
        return redirect(url_for('admin'))

    flash('User created successfully.')
    return redirect(url_for('admin'))


@app.route('/admin/update_user/<int:user_id>', methods=['POST'])
@admin_required
def update_user(user_id):
    verification_limit = request.form['verification_limit']
    db = get_db()
    db.execute('UPDATE user SET verification_limit = ? WHERE id = ?',
               (verification_limit, user_id))
    db.commit()
    flash('User updated successfully.')
    return redirect(url_for('admin'))


@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    db = get_db()
    db.execute('DELETE FROM user WHERE id = ?', (user_id,))
    db.commit()
    flash('User deleted successfully.')
    return redirect(url_for('admin'))


@app.route('/admin/user_list', methods=['GET'])
@admin_required
def admin_user_list():
    db = get_db()
    users = db.execute('SELECT * FROM user').fetchall()
    return jsonify([{
        'id': user['id'],
        'username': user['username'],
        'verification_limit': user['verification_limit'],
        'verification_count': user['verification_count'],
        'is_admin': user['is_admin']
    } for user in users])




@app.route('/download_filtered_results')
@login_required
def download_filtered_results():
    # Mapping from the English filter parameters to the Chinese status messages stored in the database
    status_map = {
        'unknown': '未知错误',
        'locked': '帐号被锁',
        'correct': '密码正确',
        'incorrect': '密码错误'
    }

    status_filter = request.args.get('status', 'all')
    # Translate the filter parameter to the corresponding Chinese status message
    status_filter_chinese = status_map.get(status_filter, None)

    # Fetch the currently logged-in user's identifier from the session or other context
    current_username = session.get('username')  # or however you are storing the logged-in user's ID
    # Fetch your data from database or wherever it's stored
    db = get_db()
    query = 'SELECT id, apple_id, password, verified FROM verification WHERE logged_in_user = ?'
    params = [current_username]
    # Apply status filter if provided
    if status_filter_chinese and status_filter != 'all':
        query += ' AND verified = ?'
        params.append(status_filter_chinese)
    data = db.execute(query, params).fetchall()

    # Convert the SQL data to a Pandas DataFrame
    df = pd.DataFrame(data, columns=['id', 'apple_id', 'password', 'verified'])  # Update with your actual columns

    # Convert DataFrame to CSV
    csv_data = df.to_csv(index=False)

    # Create a generator to stream the CSV data
    def generate():
        yield csv_data

    # Create a response object with the CSV generator
    response = Response(generate(), mimetype='text/csv')
    response.headers.set('Content-Disposition', 'attachment', filename='filtered_results.csv')
    return response



if __name__ == '__main__':
    init_db()
    app.run(debug=True)  # Turn off debug in production environment
