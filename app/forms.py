from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed, DataRequired
from wtforms import SubmitField, SelectField

class UploadForm(FlaskForm):
    nzqa = FileField(validators=[FileRequired(), FileAllowed(["csv"])])
    submit = SubmitField("Upload")

class FilterForm(FlaskForm):
   def __init__(self, subjects, *args, **kwargs):
        """Initialise with subject choices."""
        super(FilterForm, self).__init__(*args, **kwargs)
        self.subject = SelectField("Subject", choices=subjects, validators=[DataRequired()])