from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed, DataRequired
from wtforms import SubmitField, SelectField


class UploadForm(FlaskForm):

    nzqa = FileField(validators=[FileRequired(), FileAllowed(["csv"])])
    submit = SubmitField("Upload")


def create_filter_form(subjects, ethnicities):
    class FilterForm(FlaskForm):
        subject = SelectField("Subject", choices=["No filter"] + subjects, validators=[DataRequired()])
        assess_type = SelectField("Assessment Type", choices=["No filter","Internal", "External"])
        ethnicity = SelectField("Ethnicity", choices=["No filter"] + ethnicities)
        level = SelectField("NCEA Level", choices=["No filter", "Level 1", "Level 2", "Level 3"])
        compare = SelectField("Comparison", choices=["No Comparison", "Decile 8-10 Comparison"])
        submit = SubmitField("Generate")

    return FilterForm()