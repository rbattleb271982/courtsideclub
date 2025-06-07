
from app import app  # noqa: F401
from flask import send_from_directory

@app.route('/robots.txt')
def robots_txt():
    return send_from_directory('static', 'robots.txt')

if __name__ == '__main__':
    # Make sure we're binding to 0.0.0.0 to accept connections from all sources
    app.run(host='0.0.0.0', port=8080, debug=True, use_reloader=True)
