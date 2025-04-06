import os
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS  # Allow frontend requests from different origins
from chatbot import get_chatbot_response

# Get the directory of the current file (backend folder)
current_dir = os.path.dirname(os.path.abspath(__file__))

# Compute the path to the frontend folder
frontend_path = os.path.join(current_dir, '../frontend')

# Create the Flask app
#app = Flask(__name__, template_folder=frontend_path, static_folder=frontend_path)
app = Flask(__name__, template_folder=os.path.join(frontend_path, 'templates'),
            static_folder=os.path.join(frontend_path, 'static'))

# Enable CORS
CORS(app)

# Secret key for session management
app.secret_key = os.urandom(24)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Retrieve username and password from form
        username = request.form.get("username")
        password = request.form.get("password")

        # Validate user credentials (this should be hashed & stored in a database)
        # If valid:
        session['username'] = username
        return redirect(url_for("index"))
    
    return render_template("login.html")

@app.route("/")
def index():
    # Render index.html from the frontend folder
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    """Handles chatbot interactions."""
    data = request.json
    message = data.get("message", "")

    if not message:
        return jsonify({"error": "Message is required"}), 400

    # Get chatbot response using the function from chatbot.py
    response = get_chatbot_response(message)
    
    return jsonify({"response": response})

if __name__ == "__main__":
    app.run(debug=True)
