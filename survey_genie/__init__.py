import os

from flask import (
    Flask,
    json,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from flask_misaka import Misaka

DEBUG = True

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))

# Load the questions from the JSON file
with open("survey_genie/content/condensed_tlfs_sic_soc.json") as file:
    survey_data = json.load(file)
    questions = survey_data["questions"]
    ai_assist = survey_data["ai_assist"]

Misaka(app)

app.jinja_env.add_extension("jinja2.ext.do")
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True
app.config["FREEZER_IGNORE_404_NOT_FOUND"] = True
app.config["FREEZER_DEFAULT_MIMETYPE"] = "text/html"
app.config["FREEZER_DESTINATION"] = "../build"
app.cache = {}

@app.route("/")
def index():
    # When the user navigates to the home page, reset the session data
    if "current_question_index" in session:
        # Reset the current question index in the session
        session["current_question_index"] = 0

    # Clear the response data in the session
    if "response" in session:
        session.pop("response")

    session.modified = True

    return render_template("index.html")

@app.errorhandler(404)
@app.route("/page-not-found")
def page_not_found(e=None):
    return render_template("404.html"), 404 if e else 200
