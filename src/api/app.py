"""
Brazil Property API - Application Factory
"""
from src.api.base import create_app

# Create application instance
def create_app_instance():
    """Create Flask app instance for production."""
    return create_app()

# For Gunicorn
app = create_app()

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8000, debug=False)