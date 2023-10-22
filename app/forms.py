"""WTForms objects."""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed, DataRequired
from wtforms import SubmitField, SelectField, PasswordField


class UploadForm(FlaskForm):
    """Form for uploading NZQA data."""

    nzqa = FileField(validators=[FileRequired(), FileAllowed(["csv"])])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Upload")


class DeleteForm(FlaskForm):
    """Form for Clearing NZQA data."""

    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Clear Database")


def create_filter_form(subjects, ethnicities, year_list):
    """Create a FilterForm class based on provided subjects and ethnicites."""

    class FilterForm(FlaskForm):
        """Form for selecting filters to return graphs."""
        subject = SelectField("Subject", choices=["No Filter"] + subjects,
                              validators=[DataRequired()])
        assess_type = SelectField("Assessment Type",
                                  choices=["No Filter", "Internal", "External"])
        ethnicity = SelectField("Ethnicity",
                                choices=["No Filter"] + ethnicities)
        level = SelectField("NCEA Level",
                            choices=["No Filter", "Level 1", "Level 2", "Level 3"])
        compare = SelectField("Comparison",
                              choices=["No Comparison",
                                       "Compare by Decile",
                                       "Compare by Ethnicity",
                                       "Compare by Level"])
        years = SelectField("Year", choices=["No Filter"] + year_list)
        submit = SubmitField("Generate")

    return FilterForm()
