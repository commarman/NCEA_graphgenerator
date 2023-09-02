"""Routes for the graph generator."""

from app import app
from flask import render_template, redirect, json, flash
from flask_sqlalchemy import SQLAlchemy
from app.forms import UploadForm, create_filter_form, DeleteForm
from werkzeug.security import generate_password_hash, check_password_hash
import os
import app.data_uploader as upload
from app.utilities import generate_title
import numpy as np

basedir = os.path.abspath(os.path.dirname(__file__))
db = SQLAlchemy()
DB_URI = os.path.join(basedir, "results.db")
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///" + DB_URI
db.init_app(app)
import app.models as models
app.config.from_pyfile('config.py')
HASHED_DATABASE_PASSWORD = """
pbkdf2:sha256:260000$Hf0NEOHyI5TLiHdD$16df7450344156ac3744527e4fefddc5b9bc9d79610dbbfb8b1007abbe1d1f3a
"""


def construct_filter_form():
    """Retrieve subject and ethnicity data and returns a filter form."""
    # Subjects.
    subjects = models.Subject.query.all()
    subject_names = [subject.name for subject in subjects]
    subject_names.sort()
    # Ethnicities.
    ethnicities = models.Ethnicity.query.all()
    ethnicity_list = [ethnicity.name for ethnicity in ethnicities]
    ethnicity_list.sort()
    return create_filter_form(subject_names, ethnicity_list)


# Routes.
@app.errorhandler(405)
def disallowed_method(e):
    """Render the 404 page."""
    return render_template("404.html")


@app.errorhandler(404)
def page_not_found(e):
    """Render the 404 page."""
    return render_template("404.html")


@app.route("/")
def home():
    """Render the home page."""
    return render_template("home.html", page="home")


@app.route("/nzqa-data")
def nzqa_data():
    """Render the graph display page with no graph."""
    if len(models.Result.query.all()) == 0:
        flash("There is currently no data. Upload data first.")
        return redirect("/submit-nzqa")

    filter_form = construct_filter_form()
    return render_template("compare-new.html", form=filter_form, 
                           page="graph", graph=False)


@app.route("/submit-nzqa", methods=["GET", "POST"])
def submit_data():
    """Render the data submission page."""
    upload_form = UploadForm()
    return render_template("upload.html", form=upload_form, page="upload")


@app.route("/read-data", methods=["POST"])
def read_data():
    """Read form data."""
    upload_form = UploadForm()
    if upload_form.validate_on_submit():
        file = upload_form.nzqa.data
        password = upload_form.password.data
        if not check_password_hash(HASHED_DATABASE_PASSWORD, password):
            flash("Incorrect Password")
            return redirect("/submit-nzqa")
        # Data is entered using 'data_uploader.py'.
        lines = upload.read_csv(file)
        if lines is False:
            flash("Error: File is not formatted correctly.")
            return redirect("/submit-nzqa")
        # Add any new categories that appear in the data.
        upload.add_categories(lines, db, models)
        # Add the results.
        upload.add_results(lines, db, models)
        flash("Data succesfully Uploaded!")
        return redirect("/nzqa-data")
    else:
        flash("Error: Must be a .csv file.")
        return redirect("/submit-nzqa")


@app.route("/clear-data", methods=["GET"])
def clear_data():
    """Render the data clearing page."""
    delete_form = DeleteForm()
    return render_template("clear-data.html", form=delete_form, 
                           page="data_clear")


@app.route("/delete-data", methods=["POST"])
def delete_data():
    """Clear the database if the form is correct."""
    delete_form = DeleteForm()
    if delete_form.validate_on_submit():
        password = delete_form.password.data
        if not check_password_hash(HASHED_DATABASE_PASSWORD, password):
            flash("Incorrect Password")
            return redirect("/clear-data")

        upload.clear_results(db, models)
        flash("Database succesfully cleared.")
        return redirect("/submit-nzqa")
    else:
        flash("An unexpected error occured.")
        return redirect("/clear-data")


def render_graph(graph, additional_information):
    """Render the graph display page with a graph."""
    filter_form = construct_filter_form()
    graph_data = json.dumps(graph)
    return render_template("compare-new.html", form=filter_form, page="graph",
                           graph=True, info=graph_data,
                           additional=additional_information)


@app.route("/retrieve-graph-data", methods=["POST"])
def retrieve_graph_data():
    """Retrieve data for a specified set of filters."""
    form = construct_filter_form()
    if not form.validate_on_submit():
        flash("Error: Filter Form invalid.")
        return redirect("/nzqa-data")

    subject = form.subject.data
    assess_type = form.assess_type.data
    level = form.level.data
    ethnicity = form.ethnicity.data
    comparative = form.compare.data

    # Get a set of results to apply filters to.
    if comparative == "Compare by Decile":
        base_results = models.Result.query
    else:
        base_results = models.Result.query.filter_by(grouping_id=1)

    # Apply each filter.
    if subject != "No filter":
        subject_id = models.Subject.query.filter_by(name=subject).first_or_404().id
        base_results = base_results.filter_by(subject_id=subject_id)
    if assess_type != "No filter":
        assess_code = 1 if assess_type == "External" else 0
        base_results = base_results.filter_by(external=assess_code)
    if ethnicity != "No filter":
        ethnicity_id = models.Ethnicity.query.filter_by(name=ethnicity).first_or_404().id
        base_results = base_results.filter_by(ethnicity_id=ethnicity_id)
    if level != "No filter":
        # Level is received in format 'Level X'
        base_results = base_results.filter_by(level=int(level.split(" ")[1]))

    # Once filters are applied, get all results to be processed.
    base_results = base_results.all()
    # graph is the final dictionary used to produce a graph.
    graph = {"years": [], "title": generate_title(comparative, level, subject,
                                                  assess_type, ethnicity)}
    # Create a dictionary to store results for each dataset being compared.
    result_dict = {}
    for result in base_results:
        year = result.year.year
        if comparative == "Compare by Ethnicity":
            key = result.ethnicity.name
        elif comparative == "Compare by Level":
            key = f"Level {result.level}"
        elif comparative == "Compare by Decile":
            key = result.group.name
        else:
            key = "Burnside"
        # Get the current results for the key, or create an empty dict.
        current = result_dict.get(key, {})
        # Use numpy vectorisation to quickly add arrays of grades.
        result_array = np.array([result.not_achieved,
                                 result.achieved,
                                 result.merit,
                                 result.excellence,
                                 result.total_entries])
        current[year] = current.get(year, np.zeros(5)) + result_array
        result_dict[key] = current  # Adds newly created dictionaries.
        if year not in graph["years"]:
            graph["years"].append(year)

    graph["years"].sort()
    additional_information = {"entry_totals": [[year, 0] for year in graph["years"]]}
    graph["data_set_labels"] = list(result_dict.keys())

    # Not enough colours to display over 6.
    if len(graph["data_set_labels"]) > 6:
        flash("Error: Too many datasets.")
        return redirect("nzqa-data")

    num_years = len(graph["years"])
    number_sets = len(result_dict.values())
    graph["results"] = [[[0 for _ in range(num_years)] for _ in range(4)] for _ in range(number_sets)]
    dataset_index = 0
    for key, dataset in result_dict.items():
        for year, grades in dataset.items():
            # Convert numbers to proportions.
            proportion = grades / grades[4]
            computed_values = np.round(proportion * 100)
            # Restructure data to be seperated by grade.
            year_index = graph["years"].index(year)
            for grade_index, grade in enumerate(computed_values[:-1]):
                graph["results"][dataset_index][grade_index][year_index] = grade
            # Get the total number of Burnside High School entries each year.
            if key not in ["Decile 8-10", "National"]:
                index = graph["years"].index(year)
                additional_information["entry_totals"][index][1] += int(grades[4])
        dataset_index += 1
    return render_graph(graph, additional_information)


if __name__ == "__main__":
    app.run(debug=True)
