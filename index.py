import glob
import json
import os
import re

import logging

from util import parse_file_name

logger = logging.getLogger()

def parse_fhir_ndjsons(directory_path: str) -> tuple[
    dict[str, dict[str, list[int]]],
    dict[str, dict[int, str]],
    list[str],
    list[str]
]:
    """Reads FHIR ndjson files and maps line numbers to patient references.

    Returns: dict[FhirResource, dict[line_number, patient_ref]]
    """
    patient_to_lines: dict[str, dict[str, list[int]]] = {}
    lines_to_patient: dict[str, dict[int, str]] = {}
    unindexed_resources: list[str] = []
    indexed_resources: list[str] = []

    # Regex to match files like 'AllergyIntolerance.000.ndjson'
    search_path = os.path.join(directory_path, "*.ndjson")

    for file_path in glob.glob(search_path):
        filename = os.path.basename(file_path)
        match, fhir_resource = parse_file_name(filename)

        if not match:
            logger.warning(f'Unexpected file {filename}')
            continue

        fhir_resource = filename
        patient_to_lines[filename] = {}
        lines_to_patient[filename] = {}

        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f):
                line = line.strip()
                try:
                    resource_data = json.loads(line)
                    patient_ref = None
                    if "subject" in resource_data and isinstance(resource_data["subject"], dict):
                        patient_ref = resource_data["subject"].get("reference")
                    elif "patient" in resource_data and isinstance(resource_data["patient"], dict):
                        patient_ref = resource_data["patient"].get("reference")
                    if patient_ref and patient_ref.startswith("Patient/"):
                        lines  = patient_to_lines[filename].get(patient_ref, [])
                        patient_to_lines[filename][patient_ref] = lines + [line_num]
                        lines_to_patient[filename][line_num] = patient_ref
                except json.JSONDecodeError:
                    logger.warning(f"Warning: Skipping malformed JSON on line {line_num} in {filename}")
        if not patient_to_lines[filename]:
            del patient_to_lines[filename]
            del lines_to_patient[filename]
            unindexed_resources = unindexed_resources + [fhir_resource]
        else:
            indexed_resources = indexed_resources + [fhir_resource]

    return patient_to_lines, lines_to_patient, unindexed_resources, indexed_resources
