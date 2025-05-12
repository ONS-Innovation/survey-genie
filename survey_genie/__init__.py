import os
import pprint

from flask import Flask, json, redirect, render_template, request, session, url_for
from flask_misaka import Misaka

from survey_genie.utils.utils import (
    consent_redirect,
    followup_redirect,
    get_question_routing,
    update_session_and_redirect,
)

from utils.logging import get_logger

DEBUG = True
number_to_word = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}

logger = get_logger(__name__)
logger.debug("Survey Genie started", id=12345, action="start")
logger.info("Survey Genie started")
logger.warning("Survey Genie started", id=12345, action="start")
logger.error("Survey Genie started")
logger.critical("Survey Genie started", id=12345, action="start")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))

# Load the questions from the JSON file
with open("survey_genie/content/condensed_tlfs_sic_soc.json") as file:
    survey_data = json.load(file)
    questions = survey_data["questions"]
    survey_assist = survey_data["survey_assist"]

survey_iteration = {
    "user": "",
    "questions": [],
    "time_start": None,
    "time_end": None,
    "survey_assist_time_start": None,
    "survey_assist_time_end": None,
}


Misaka(app)

app.jinja_env.add_extension("jinja2.ext.do")
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True
app.config["FREEZER_IGNORE_404_NOT_FOUND"] = True
app.config["FREEZER_DEFAULT_MIMETYPE"] = "text/html"
app.config["FREEZER_DESTINATION"] = "../build"
app.cache = {}


# Method provides a dictionary to the jinja templates, allowing variables
# inside the dictionary to be directly accessed within the template files
# This saves defining navigation variables in each route
@app.context_processor
def set_variables():
    navigation = {"navigation": {}}
    return {"navigation": navigation}


@app.route("/")
def index():
    cqi_ind = 0
    resp_ind = 0
    surv_iter_ind = 0
    # When the user navigates to the home page, reset the session data
    if "current_question_index" in session:
        # Reset the current question index in the session
        session["current_question_index"] = 0
        cqi_ind = 1

    # Clear the response data in the session
    if "response" in session:
        session.pop("response")
        resp_ind = 1

    # Clear the survey iteration data in the session
    if "survey_iteration" in session:
        session.pop("survey_iteration")
        surv_iter_ind = 1

    session.modified = True
    print(f"session presence current_question_index: {cqi_ind}, response: {resp_ind}, survey_iteration: {surv_iter_ind}")

    return render_template("index.html")


# Generic route to handle survey questions
@app.route("/survey", methods=["GET", "POST"])
def survey():
    # Initialise the current question index in the session if it doesn't exist
    if "current_question_index" not in session:
        session["current_question_index"] = 0

        session.modified = True

    # Get the current question based on the index
    current_index = session["current_question_index"]
    current_question = questions[current_index]

    # if question_text contains PLACEHOLDER_TEXT, get the associated
    # placeholder_field associated with the question and replace the
    # PLACEHOLDER_TEXT string with the value of the specified field
    # held in session response
    if "PLACEHOLDER_TEXT" in current_question["question_text"]:
        # Copy the current question to a new dictionary
        current_question = current_question.copy()

        placeholder_field = current_question["placeholder_field"]

        if placeholder_field is not None:
            current_question["question_text"] = current_question[
                "question_text"
            ].replace("PLACEHOLDER_TEXT", session["response"][placeholder_field])

    return render_template("question_template.html", **current_question)


# Route called after each question (or interaction) to save response to session data.
# The response is saved to the session dictionary and the user is redirected to the
# next question or interaction.
# TODO - The actions dictionary is currently hardcoded for survey questions, this
# needs to be updated to be more dynamic.  There is also cruft in the variables passed
# to the update_session_and_redirect function.
@app.route("/save_response", methods=["POST"])
def save_response():

    # Define a dictionary to store responses
    if "response" not in session:
        session["response"] = {}

    if "survey_iteration" not in session:
        session["survey_iteration"] = survey_iteration

    actions = {
        "core_question": lambda: update_session_and_redirect(
            session, request, questions, survey_assist, *routing
        ),
        "survey_assist_consent": lambda: consent_redirect(),
        "follow_up_question": lambda: followup_redirect(),
    }

    # Store the user response to the question AI asked
    question = request.form.get("question_name")

    # If the question is not consent or AI
    if question not in ["survey_assist_consent", "follow_up_question"]:
        routing = get_question_routing(question, questions)
        question = "core_question"

    if question.startswith("survey_assist"):
        question = "follow_up_question"

        # get survey data
        survey_data = session.get("survey_iteration")
        # get questions
        survey_questions = survey_data["questions"]

        # get the last question
        last_question = survey_questions[-1]
        # update the response name, required by forward_redirect
        # TODO - can this be incorporated in the forward_redirect function?
        last_question["response"] = request.form.get(last_question["response_name"])

    if question in actions:
        return actions[question]()
    else:
        return "Invalid question ID", 400


@app.route("/survey_assist_consent")
def survey_assist_consent():

    if "PLACEHOLDER_FOLLOWUP" in survey_assist["consent"]["question_text"]:
        # Get the maximum followup
        max_followup = survey_assist["consent"]["max_followup"]

        if max_followup == 1:
            followup_text = "one additional question"
        else:
            # convert numeric to string
            number_word = number_to_word.get(max_followup, "unknown")

            followup_text = f"a maximum of {number_word} additional questions"

        # Replace PLACEHOLDER_FOLLOWUP wit the content of the placeholder field
        survey_assist["consent"]["question_text"] = survey_assist["consent"][
            "question_text"
        ].replace("PLACEHOLDER_FOLLOWUP", followup_text)

    if "PLACEHOLDER_REASON" in survey_assist["consent"]["question_text"]:
        # Replace PLACEHOLDER_REASON wit the content of the placeholder field
        survey_assist["consent"]["question_text"] = survey_assist["consent"][
            "question_text"
        ].replace("PLACEHOLDER_REASON", survey_assist["consent"]["placeholder_reason"])

    # print("AI Assist consent question text:", survey_assist["consent"]["question_text"])
    return render_template(
        "survey_assist_consent.html",
        title=survey_assist["consent"]["title"],
        question_name=survey_assist["consent"]["question_name"],
        question_text=survey_assist["consent"]["question_text"],
        justification_text=survey_assist["consent"]["justification_text"],
    )


@app.route("/previous_question")
def previous_question():
    # When the user navigates to the home page, reset the session data
    if "current_question_index" in session and session["current_question_index"] > 0:
        # Point to the prior question
        session["current_question_index"] -= 1
        return redirect(url_for("survey"))
    else:
        return render_template("index.html")


@app.errorhandler(404)
@app.route("/page-not-found")
def page_not_found(e=None):
    return render_template("404.html"), 404 if e else 200
