from survey_genie import app

if __name__ == "__main__":
    # Run the Flask app directly when the script is executed
    app.run(host="0.0.0.0", port=8000)  # noqa: S104
