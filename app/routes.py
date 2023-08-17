from app import app
from flask import render_template, g, request, redirect, url_for, session, json, flash
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


@app.errorhandler(404)
def page_not_found(e):
    """Render the 404 page."""
    return render_template("404.html")


@app.route("/")
def home():
    """Render the home page."""
    return render_template("home.html", page="home")

def construct_filter_form():
    """Construct a filter form."""
    # Subjects.
    subjects = models.Subject.query.all()
    subject_names = [subject.name for subject in subjects]
    subject_names.sort()
    # Ethnicities.
    ethnicities = models.Ethnicity.query.all()
    ethnicity_list = [ethnicity.name for ethnicity in ethnicities]
    ethnicity_list.sort()
    return create_filter_form(subject_names, ethnicity_list)


@app.route("/nzqa-data")
def nzqa_data():
    """Render the comparison graph generator page."""
    if len(models.Result.query.all()) == 0:
        flash("There is currently no data. Upload data first.")
        return redirect("/submit-nzqa")
    form = construct_filter_form()
    return render_template("compare-new.html", form=form, page="graph", graph=False)


@app.route("/submit-nzqa", methods=["GET","POST"])
def submit_data():
    """Submit NCEA data for upload."""

    form = UploadForm()

    return render_template("upload.html", form=form, page="upload")


@app.route("/read-data", methods=["POST"])
def read_data():
    """Read form data."""
    form = UploadForm()
    if form.validate_on_submit():
        file = form.nzqa.data
        lines = upload.read_csv(file)
        upload.add_categories(lines, db, models)
        upload.add_results(lines, db, models)
        flash("Data succesfully Uploaded!")
        return redirect("/nzqa-data")
    else:
        flash("Error: File didn't validate.")
        return redirect("/submit-nzqa")


def render_graph(result_years, subject, title, entry_totals):
    """Render the html page with a graph."""
    form = construct_filter_form()
    years = [result[0] for result in result_years[0]]
    bhs_values = [result[1] for result in result_years[0]]
    not_achieved = [value[0] for value in bhs_values]
    achieved = [value[1] for value in bhs_values]
    merit = [value[2] for value in bhs_values]
    excellence = [value[3] for value in bhs_values]
    graph_dict = {"labels": years, "title":title}
    for i, result_set in enumerate(result_years):
        grades = [result[1] for result in result_set]
        graph_dict[f"not_achieved{i+1}"] = result_set[0]
        graph_dict[f"achieved{i+1}"] = result_set[1]
        graph_dict[f"merit{i+1}"] = result_set[2]
        graph_dict[f"excellence{i+1}"] = result_set[3]
    additional_dict = {"entries": entry_totals}
    graph_data = json.dumps(graph_dict)
    return render_template("compare-new.html", form=form, page="graph", info=graph_data, graph=True, additional=additional_dict, comparison=len(result_years) > 1)


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
        result_dict= {}
        # Result dicts is a dict of each dataset being compared with by year and grade.
        print(len(base_results))
        for result in base_results:
            year = result.year.year
            if comparative == "Compare by Ethnicity":
                key = result.ethnicity.name
            elif comparative == "Compare by Level":
                key = result.level
            elif comparative == "Compare by Decile":
                key = result.group
            current = result_dict.get(key, [])
            current[year] = current.get(year, np.zeros(5)) + np.array([result.not_achieved, result.achieved, result.merit, result.excellence, result.total_entries])
            result_dict[key] = current
        
        # Convert numbers to proportions.
        i = 0
        for key, dataset in result_dict.items():
            for year, grades in dataset.items():
                proportion = grades / grades[4]  # Divide by total entries.
                computed_values = np.round(proportion * 100)
                dataset[year] = computed_values
            if i == 0:
                print(dataset)
                i += 1

        total_entries_bhs = {}
        total_entries_decile = {}
        bhs_results = {}
        decile_results = {}
        percent_tuples = [[]]
        for result in base_results:
            year = result.year.year
            bhs_results[year] = bhs_results.get(year, np.zeros(4)) + np.array([result.not_achieved, result.achieved, result.merit, result.excellence])
            total_entries_bhs[year] = total_entries_bhs.get(year, 0) + result.total_entries
        for year in total_entries_bhs.keys():
            proportion = bhs_results[year] / total_entries_bhs[year]
            computed_values = np.round(proportion * 100)
            percent_tuples[0].append((year, (list(computed_values))))
        if comparative == "Compare by Decile":
            percent_tuples.append([])
            for result in comp_results:
                year = result.year.year
                decile_results[year] = decile_results.get(year, np.zeros(4)) + np.array([result.not_achieved, result.achieved, result.merit, result.excellence])
                total_entries_decile[year] = total_entries_decile.get(year, 0) + result.total_entries
            for year in total_entries_decile.keys():
                computed_values = np.round(decile_results[year] / total_entries_decile[year] * 100)
                percent_tuples[1].append((year, (list(computed_values))))
        for tuple_list in percent_tuples:
            tuple_list.sort()
        total_entries = [(year, entries) for year, entries in total_entries_bhs.items()]
        return render_graph(percent_tuples, subject, title, total_entries)
    flash("It didn't work as expected/")
    return redirect("/nzqa-data")


if __name__ == "__main__":
    app.run(debug=True)