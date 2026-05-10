import os

from app import create_app, socketio

# Starts the Flask-SocketIO development server.
app = create_app()

if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "1") == "1"
    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        debug=debug,
        use_reloader=False,
        allow_unsafe_werkzeug=True,
    )
