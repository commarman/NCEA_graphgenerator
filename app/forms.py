from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed, DataRequired
from wtforms import SubmitField, SelectField

class UploadForm(FlaskForm):
    nzqa = FileField(validators=[FileRequired(), FileAllowed(["csv"])])
    submit = SubmitField("Upload")

def create_filter_form(subjects):
    class FilterForm(FlaskForm):
        subject = SelectField("Subject", choices=subjects, validators=[DataRequired()])
        submit = SubmitField("Generate")

    return FilterForm()