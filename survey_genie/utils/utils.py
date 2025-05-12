import pprint
from datetime import datetime, timezone

from flask import redirect, url_for


def update_session_and_redirect(session, request, questions, ai_assist, value, route):
    # Set key as value but with hyphens replaced with underscores
    key = value.replace("-", "_")
    session["response"][key] = request.form.get(value)

    # Retrieve the survey data from the session
    survey_iteration = session.get("survey_iteration")

    if not survey_iteration:
        # Reinitialise survey in session if not present
        session["survey_iteration"] = {
            "user": "",
            "questions": [],
            "time_start": None,
            "time_end": None,
            "survey_assist_time_start": None,
            "survey_assist_time_end": None,
        }
        survey_iteration = session["survey_iteration"]
        # Set the time start based on the current timestamp
        survey_iteration["time_start"] = datetime.now(timezone.utc)
        print("Initialise survey data in update_session_and_redirect")
        print("Survey data:", session.get("survey_iteration"))
        session.modified = True

    # Get the current question and take a copy so
    # that the original question data is not modified
    current_question = questions[session["current_question_index"]]
    current_question = current_question.copy()

    placeholder_field = current_question["placeholder_field"]

    if "response" in session and placeholder_field in session["response"]:
        current_question["question_text"] = current_question["question_text"].replace(
            "PLACEHOLDER_TEXT", session["response"][placeholder_field]
        )
        # print("Updated question text:", current_question["question_text"])

    # Append the question and response to the list of questions
    survey_iteration["questions"].append(
        {
            "question_id": current_question.get("question_id"),
            "question_text": current_question.get("question_text"),
            "response_type": current_question.get("response_type"),
            "response_options": current_question.get("response_options"),
            "response_name": current_question.get("response_name"),
            "response": request.form.get(value),
            "used_for_classifications": current_question.get(
                "used_for_classifications"
            ),
        }
    )
    print("===== Survey Iteration =====")
    pprint.pprint(session["survey_iteration"], indent=4, width=80)
    print("=============================")

    # If ai assist is enabled and the current question has an interaction
    # then redirect to the consent page to ask the user if they want to
    # continue with the AI assist interaction
    if ai_assist.get("enabled", True):
        session.modified = True
        interactions = ai_assist.get("interactions")
        if len(interactions) > 0 and current_question.get(
            "question_id"
        ) == interactions[0].get("after_question_id"):
            # print("AI Assist interaction detected - REDIRECTING to consent")
            return redirect(url_for("survey_assist_consent"))

    session["current_question_index"] += 1
    session.modified = True
    return redirect(url_for(route))


# The question array defines the identifier for a question and the position
# indicates whether the next action is to ask another question or display the
# sumarry of the survey responses.
def get_question_routing(question_name, questions):
    for i, question in enumerate(questions):
        if question["question_name"] == question_name:
            response_name = question["response_name"]
            route = "summary" if i == len(questions) - 1 else "survey"
            return response_name, route
    raise ValueError(f"Question name '{question_name}' not found in questions.")


def consent_redirect():
    print("Consent redirect stub")
    return redirect(url_for("page_not_found"))


def followup_redirect():
    print("Followup redirect stub")
    return redirect(url_for("page_not_found"))
