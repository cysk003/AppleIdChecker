# app.py

from flask import Flask, request, jsonify
from apple_id_checker import AppleIDChecker

app = Flask(__name__)

@app.route('/check_single', methods=['POST'])
def check_single():
    data = request.json
    apple_id = data.get('apple_id')
    password = data.get('password')

    if not apple_id or not password:
        return jsonify({"error": "需要提供Apple ID和密码。"}), 400

    checker = AppleIDChecker()
    result = checker.try_login(apple_id, password)
    return jsonify(result), 200

if __name__ == '__main__':
    app.run(debug=True)
