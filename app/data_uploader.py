"""Functions for uploading data to the database."""
import numpy as np

# Constants.
EXT_ASSESS = "Externally Assessed"
BHS_NAME = "Burnside High School"
NATIONAL_NAME = "Decile 8-10"


def read_csv(csv_file):
    """Read the csv file and check for incorrect formatting."""
    lines = csv_file.readlines()
    lines = [line.decode("utf-8").split(",") for line in lines]
    with open("/app/static/header.txt", "r") as header:
        header_format = header.readlines()
        if header_format != lines[:4]:
            return False
    if len(lines) < 5:  # At least one result row must exist.
        return False
    if len(lines[0]) != 31:   # 31 is the number of columns.
        return False
    return lines[4:]  # First four lines are headers.


def add_categories(csv_file, db, models):
    """Add missing categories for subject, year, etc."""
    # Get unique values for each group.
    subjects = set()
    ethnicities = set()
    years = set()
    for line in csv_file:
        if line[5] != '0':  # Column 5 is the number of BHS entries.
            subjects.add(line[0].capitalize())
            ethnicities.add(line[2])
            years.add(line[4])

    # Add new categories if they don't already exist.
    for subject in subjects:
        if models.Subject.query.filter_by(name=subject).first() is None:
            db.session.add(models.Subject(subject))
            db.session.commit()
    for ethnicity in ethnicities:
        if models.Ethnicity.query.filter_by(name=ethnicity).first() is None:
            db.session.add(models.Ethnicity(ethnicity))
            db.session.commit()
    for year in years:
        if models.AcademicYear.query.filter_by(year=year).first() is None:
            db.session.add(models.AcademicYear(year))
            db.session.commit()


def add_results(csv_file, db, models):
    """Add results from a csv file.

    Assumes all subjects, ethnicities, and years
    already exist in the corresponding table.
    """
    # Numpy used to speed up processing.
    csv_file = np.array(csv_file)
    # Get all lines with an entry from Burnside.
    used_lines = csv_file[(csv_file[:, 5] != '0')]
    for line in used_lines:
        subject, level, ethnicity, assess_type, year = line[:5]
        bhs_results = line[5:18]
        compare_results = line[18:]

        # Get values.
        subject_id = models.Subject.query.filter_by(name=subject.capitalize())[0].id
        ethnicity_id = models.Ethnicity.query.filter_by(name=ethnicity)[0].id
        year_id = models.AcademicYear.query.filter_by(year=year)[0].id
        level = int(level.split(" ")[1])
        external = (assess_type == EXT_ASSESS)
        bhs_entries = bhs_results[0]
        bhs_assessed = bhs_results[4]
        bhs_na = bhs_results[5]
        bhs_a = bhs_results[7]
        bhs_m = bhs_results[9]
        bhs_e = bhs_results[11]
        bhs_id = models.Grouping.query.filter_by(name=BHS_NAME)[0].id

        comp_entries = compare_results[0]
        comp_assessed = compare_results[4]
        comp_na = compare_results[5]
        comp_a = compare_results[7]
        comp_m = compare_results[9]
        comp_e = compare_results[11]
        comp_id = models.Grouping.query.filter_by(name=NATIONAL_NAME)[0].id

        bhs_result = models.Result(subject_id, year_id, ethnicity_id,
                                   bhs_id, level, external,
                                   bhs_entries, bhs_assessed,
                                   bhs_na, bhs_a, bhs_m, bhs_e)

        comp_result = models.Result(subject_id, year_id, ethnicity_id,
                                    comp_id, level, external,
                                    comp_entries, comp_assessed,
                                    comp_na, comp_a, comp_m, comp_e)
        db.session.add(bhs_result)
        db.session.add(comp_result)
    db.session.commit()
    return True


def clear_results(db, models):
    """Clear the results table."""
    models.Result.query.delete()
    models.Subject.query.delete()
    models.Ethnicity.query.delete()
    models.AcademicYear.query.delete()
    db.session.commit()
