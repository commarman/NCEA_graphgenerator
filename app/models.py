"""Models for the database."""

from app.routes import db


class Ethnicity(db.Model):
    __tablename__ = "Ethnicity"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text())

    def __init__(self, name):
        self.name = name


class AcademicYear(db.Model):
    __tablename__ = "AcademicYear"
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer)

    def __init__(self, year):
        self.year = year


class Subject(db.Model):
    __tablename__ = "Subject"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text())

    def __init__(self, name):
        self.name = name


class Grouping(db.Model):
    __tablename__ = "Grouping"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text())

    def __init__(self, name):
        self.name = name


class Result(db.Model):
    __tablename__ = "Result"
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("Subject.id"))
    year_id = db.Column(db.Integer, db.ForeignKey("AcademicYear.id"))
    ethnicity_id = db.Column(db.Integer, db.ForeignKey("Ethnicity.id"))
    grouping_id = db.Column(db.Integer, db.ForeignKey("Grouping.id"))
    level = db.Column(db.Integer)
    external = db.Column(db.Boolean)
    total_entries = db.Column(db.Integer)
    assessed = db.Column(db.Integer)
    not_achieved = db.Column(db.Integer)
    achieved = db.Column(db.Integer)
    merit = db.Column(db.Integer)
    excellence = db.Column(db.Integer)

    ethnicity = db.relationship("Ethnicity")
    subject = db.relationship("Subject")
    year = db.relationship("AcademicYear")
    group = db.relationship("Grouping")

    def __init__(self, subject_id, year_id, ethnicity_id,
                 grouping_id, level, external,
                 total_entries, assessed, not_achieved,
                 achieved, merit, excellence):
        self.subject_id = subject_id
        self.year_id = year_id
        self.ethnicity_id = ethnicity_id
        self.grouping_id = grouping_id
        self.level = level
        self.external = external
        self.total_entries = total_entries
        self.assessed = assessed
        self.not_achieved = not_achieved
        self.achieved = achieved
        self.merit = merit
        self.excellence = excellence
