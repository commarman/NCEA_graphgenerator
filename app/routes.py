from app import app
from flask import render_template, g, request, redirect, url_for, session, json, flash
from flask_sqlalchemy import SQLAlchemy
from app.forms import UploadForm, FilterForm
import os
import app.data_uploader as upload

basedir = os.path.abspath(os.path.dirname(__file__))
db = SQLAlchemy()
app.config ['SQLALCHEMY_DATABASE_URI'] = "sqlite:///" + os.path.join(basedir, "results.db")
db.init_app(app)
import app.models as models
app.config.from_pyfile('config.py')


@app.route("/")
def home():
    """Render the home page."""
    return render_template("home.html")

@app.route("/nzqa-data")
def nzqa_data():
    """Render the comparison graph generator page."""
    if len(models.Result.query.all()) == 0:
        flash("There is currently no data. Upload data first.")
        return redirect("/submit-nzqa")
    subjects = models.Subject.query.all()
    subject_names = [subject.name for subject in subjects]
    form = FilterForm(subject_names)
    return render_template("compare.html", form = form)


@app.route("/submit-nzqa", methods=["GET","POST"])
def submit_data():
    """Submit NCEA data for upload."""

    form = UploadForm()

    return render_template("upload.html", form = form)

@app.route("/read-data", methods=["POST"])
def read_data():
    """Read form data."""
    form = UploadForm()
    if form.validate_on_submit():
        file = form.nzqa.data
        lines = upload.read_csv(file)
        upload.add_results(lines, db, models)
        flash("Data succesfully Uploaded!")
        return redirect("/nzqa-data")
    else:
        flash("Error: File didn't validate.")
        return redirect("/submit-nzqa")

@app.route("/result-test")
def result_test():
    results = (
        models.Result.query
        .filter_by(subject_id = 1, external = True)
        .group_by(models.Result.grouping_id, models.Result.year_id)
        .with_entities( 
            models.Result,
            func.sum(models.Result.not_achieved),
            func.sum(models.Result.achieved)))
    for result in results:
        print(result)
        # print(result.id)
        # print(result.ethnicity)
        # print(result.year)
        # print(result.subject)
        # print((result.merit / result.total_entries))

    labels = json.dumps([f"{result[0].year.year} {result[0].group.name}" for result in results])
    data = json.dumps([result[2] for result in results])
    return render_template("chart-test.html", data = data, labels = labels)

@app.route("/ins")
def insert_test():
    insertion_dict = {
        "subject_id" :2,
        "ethnicity_id" : 3,
        "grouping_id" : 1,
        "year_id" : 2,
        "external" : True,
        "level" : 2,
        "total_entries" : 100,
        "assessed" : 89,
        "not_achieved" : 16,
        "achieved" : 21,
        "merit" : 32,
        "excellence" : 20
    }

    new_result = models.Result(insertion_dict)
    db.session.add(new_result)
    db.session.commit()
    return "hi"

@app.route("/del")
def delete_test():
    results = models.Result.query.delete()
    db.session.commit()
    return "wow"

def APP():
    return app

if __name__ == "__main__":
    app.run(debug=True)