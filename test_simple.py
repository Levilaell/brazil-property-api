#!/usr/bin/env python3
"""Simple test script to verify API is working."""

import sys
import os
sys.path.append('src')

from flask import Flask, jsonify
from datetime import datetime

app = Flask(__name__)

@app.route('/api/v1/test')
def test():
    return jsonify({
        'message': 'API is working!',
        'timestamp': datetime.utcnow().isoformat(),
        'status': 'success'
    })

@app.route('/api/v1/demo')
def demo():
    return jsonify({
        'demo': True,
        'properties': [
            {'id': 1, 'title': 'Casa Demo', 'price': 500000, 'city': 'São Paulo'}
        ],
        'message': 'Demo endpoint working!'
    })

if __name__ == '__main__':
    print("Starting simple test server...")
    app.run(host='0.0.0.0', port=5000, debug=True)