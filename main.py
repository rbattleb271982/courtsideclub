
from app import app  # noqa: F401

if __name__ == '__main__':
    # Make sure we're binding to 0.0.0.0 to accept connections from all sources
    app.run(host='0.0.0.0', port=5000, debug=True)
