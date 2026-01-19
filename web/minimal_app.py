from flask import Flask, render_template, request, jsonify
import time

app = Flask(__name__)

# Minimal version with just the basic route
@app.route('/')
def index():
    return '<h1>Minimal App Running</h1><p>If you see this quickly, the issue is elsewhere.</p>'

if __name__ == '__main__':
    print("Starting minimal app...")
    app.run(debug=False, host='0.0.0.0', port=5000)