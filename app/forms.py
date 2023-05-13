from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import SubmitField

class UploadForm(FlaskForm):
    nzqa = FileField(validators=[FileRequired(), FileAllowed(["csv"])])
    submit = SubmitField("Upload")

class FilterForm(FlaskForm):
    pass