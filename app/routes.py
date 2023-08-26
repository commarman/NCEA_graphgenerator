from app import app
from flask import render_template, redirect, url_for, json, flash
from flask_sqlalchemy import SQLAlchemy
from app.forms import UploadForm, create_filter_form
import os
import app.data_uploader as upload
import numpy as np
import re

basedir = os.path.abspath(os.path.dirname(__file__))
db = SQLAlchemy()
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///" + os.path.join(basedir, "results.db")
db.init_app(app)
import app.models as models
app.config.from_pyfile('config.py')


def construct_filter_form():
    """Retrieves subject and ethnicity data and returns a filter form."""
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
    return render_template("compare-new.html", form=filter_form, page="graph", graph=False)


@app.route("/submit-nzqa", methods=["GET","POST"])
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
        # Data is entered using 'data_uploader.py'.
        lines = upload.read_csv(file)
        # Add any new categories that appear in the data.
        upload.add_categories(lines, db, models)
        # Add the results.
        upload.add_results(lines, db, models)
        flash("Data succesfully Uploaded!")
        return redirect("/nzqa-data")
    else:
        flash("Error: Must be a .csv file.")
        return redirect("/submit-nzqa")


def render_graph(graph, subject, title, additional_information, set_count):
    """Render the graph display page with a graph."""
    filter_form = construct_filter_form()
    graph_data = json.dumps(graph)
    print(additional_information["entry_totals"])
    return render_template("compare-new.html", form=filter_form, page="graph", graph=True, info=graph_data, additional=additional_information)


@app.route("/retrieve-graph-data", methods=["POST"])
def retrieve_graph_data():
    """Retrieve data by filters for graphing."""

    form = construct_filter_form()
    if form.validate_on_submit():
        # Get values from form.
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
        # Get comparative results.

        if comparative == "Compare by Decile":
            #base_results.group_by(models.Result.grouping_id)
            title = f"Burnside against Decile 8-10 {level} {subject} {assess_type} results for {ethnicity} students"
        elif comparative == "Compare by Ethnicity":
            base_results.group_by(models.Result.ethnicity_id)
            title = f"Burnside {level} {subject} {assess_type} results across Ethnicity"
        elif comparative == "Compare by Level":
            #base_results.group_by(models.Result.level)
            title = f"Burnside {subject} {assess_type} results across Level for {ethnicity} students"
        else:
            title = f"Burnside {level} {subject} {assess_type} results for {ethnicity} students"
        title = re.sub("No filter ", "", title)  # Use regex to remove 'No filter' appearances.
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
            base_results = base_results.filter_by(level=int(level.split(" ")[1]))  # Level is received in format 'Level X'


        base_results = base_results.all()
        # Convert results to graphable information.
        result_dict = {}
        graph = {"years":[], "title":title}
        # Result dicts is a dict of each dataset being compared with by year and grade.
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
            current = result_dict.get(key, {})
            current[year] = current.get(year, np.zeros(5)) + np.array([result.not_achieved, result.achieved, result.merit, result.excellence, result.total_entries])
            result_dict[key] = current
            if not year in graph["years"]:
                graph["years"].append(year)
        
        graph["years"].sort()
        # Convert numbers to proportions.
        num_years = len(graph["years"])
        additional_information = {"entry_totals":[[year, 0] for year in graph["years"]]}
        for key, dataset in result_dict.items():
            for year, grades in dataset.items():
                proportion = grades / grades[4]  # Divide by total entries.
                computed_values = np.round(proportion * 100)
                dataset[year] = computed_values
                if not key in ["Decile 8-10", "National"]:
                    index = graph["years"].index(year)
                    additional_information["entry_totals"][index][1] += int(grades[4])
                

        graph["data_set_labels"] = list(result_dict.keys())
        number_sets = len(result_dict.values())
        graph["results"] = [[[0 for _ in range(num_years)] for _ in range(4)] for _ in range(number_sets)]
        for i, dataset in enumerate(result_dict.values()):
            for year, grades in dataset.items():
                year_index = graph["years"].index(year)
                for j, grade in enumerate(grades[:-1]):
                    graph["results"][i][j][year_index] = grade

        return render_graph(graph, subject, title, additional_information, number_sets)
    flash("It didn't work as expected/")
    return redirect("/nzqa-data")


if __name__ == "__main__":
    app.run(debug=True)