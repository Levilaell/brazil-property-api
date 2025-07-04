#!/usr/bin/env python3
"""
Run the Brazil Property API server
"""
from src.api.base import create_app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5001, debug=True)