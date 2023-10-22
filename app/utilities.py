"""Utility functions.

Created on 26/08/2023
"""
import re


def generate_title(comparative, level, subject, assessment_type, ethnicity):
    """Generates a title based on filters and
    what kind of comparison is being made."""
    if comparative == "Compare by Decile":
        title = f"Burnside against Decile 8-10 {level} {subject} {assessment_type} results for {ethnicity} students"
    elif comparative == "Compare by Ethnicity":
        title = f"Burnside {level} {subject} {assessment_type} results across Ethnicity"
    elif comparative == "Compare by Level":
        title = f"Burnside {subject} {assessment_type} results across Level for {ethnicity} students"
    else:
        title = f"Burnside {level} {subject} {assessment_type} results for {ethnicity} students"
        # Use regex to remove 'No filter' appearances.
    title = re.sub("No Filter ", "", title)
    return title
