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
app.config ['SQLALCHEMY_DATABASE_URI'] = "sqlite:///" + os.path.join(basedir, "results.db")
db.init_app(app)
import app.models as models
app.config.from_pyfile('config.py')


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
    return render_template("compare.html", form = form, page="graph", graph=False)


@app.route("/submit-nzqa", methods=["GET","POST"])
def submit_data():
    """Submit NCEA data for upload."""

    form = UploadForm()

    return render_template("upload.html", form = form, page="upload")

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
    if len(result_years[1]) > 0:
        comp_values = [result[1] for result in result_years[1]]
        comp_na = [result[0] for result in comp_values]
        comp_a = [value[1] for value in comp_values]
        comp_m = [value[2] for value in comp_values]
        comp_e = [value[3] for value in comp_values]
        graph_dict = {"labels":years, "not_achieved":not_achieved, "achieved":achieved, "merit":merit, "excellence":excellence, "subject":subject, "title":title,
                      "comp_not_achieved": comp_na, "comp_achieved":comp_a, "comp_merit": comp_m, "comp_excellence":comp_e}
    else:
        graph_dict = {"labels":years, "not_achieved": not_achieved, "achieved":achieved, "merit":merit, "excellence":excellence, "subject":subject, "title":title}
    additional_dict = {"entries": entry_totals}
    graph_data = json.dumps(graph_dict)
    return render_template("compare.html", form = form, page="graph", info = graph_data, graph = True, additional = additional_dict, comparison = len(result_years[1]) > 0)


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

        base_results = models.Result.query.filter_by(grouping_id = 1)
        comp_results = models.Result.query.filter_by(grouping_id = 2)
        if subject != "No filter":
            subject_id = models.Subject.query.filter_by(name = subject).first_or_404().id
            base_results = base_results.filter_by(subject_id = subject_id)
            comp_results = comp_results.filter_by(subject_id = subject_id)
        if assess_type != "No filter":
            assess_code = 1 if assess_type == "External" else 0
            base_results = base_results.filter_by(external = assess_code)
            comp_results = comp_results.filter_by(external = assess_code)
        if ethnicity != "No filter":
            ethnicity_id = models.Ethnicity.query.filter_by(name = ethnicity).first_or_404().id
            base_results = base_results.filter_by(ethnicity_id = ethnicity_id)
            comp_results = comp_results.filter_by(ethnicity_id = ethnicity_id)
        if level != "No filter":
            base_results = base_results.filter_by(level = int(level.split(" ")[1])) #  Level is received in format 'Level X'
            comp_results = comp_results.filter_by(level = int(level.split(" ")[1]))
        
        if comparative == "Decile 8-10 Comparison":
            title = f"Burnside against Decile 8-10 {level} {subject} {assess_type} results for {ethnicity} students"
        else:
            title = f"Burnside {level} {subject} {assess_type} results for {ethnicity} students"
        title = re.sub("No filter ", "", title)  # Use regex to remove 'No filter' appearances.

        total_entries_bhs = {}
        total_entries_decile = {}
        bhs_results = {}
        decile_results = {}
        total_years = {}
        percent_tuples = [[],[]]
        for result in base_results:
            year = result.year.year
            bhs_results[year] = bhs_results.get(year, np.zeros(4)) + np.array([result.not_achieved, result.achieved, result.merit, result.excellence])
            total_entries_bhs[year] = total_entries_bhs.get(year, 0) + result.total_entries
        for year in total_entries_bhs.keys():
            a = bhs_results[year]/ total_entries_bhs[year]
            computed_values = np.round(bhs_results[year] / total_entries_bhs[year] * 100)
            percent_tuples[0].append((year, (list(computed_values))))
        if comparative == "Decile 8-10 Comparison":
            for result in comp_results:
                year = result.year.year
                decile_results[year] = decile_results.get(year, np.zeros(4)) + np.array([result.not_achieved, result.achieved, result.merit, result.excellence])
                total_entries_decile[year] = total_entries_decile.get(year, 0) + result.total_entries
            for year in total_entries_decile.keys():
                computed_values = np.round(decile_results[year] / total_entries_decile[year] * 100)
                percent_tuples[1].append((year, (list(computed_values))))
        percent_tuples[0].sort()
        percent_tuples[1].sort()
        total_entries = [(year, entries) for year, entries in total_entries_bhs.items()]
        return render_graph(percent_tuples, subject, title, total_entries)
    flash("It didn't work as expected/")
    return redirect("/nzqa-data")

if __name__ == "__main__":
    app.run(debug=True)