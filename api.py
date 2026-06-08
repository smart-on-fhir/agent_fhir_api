import json
import logging
import os.path

from flask import Flask, Blueprint, request, jsonify

from index import parse_fhir_ndjsons
from pagination import FHIRPagination, PaginationObject

logger = logging.getLogger()

app = Flask(__name__)

logger.info('Finding FHIR ndjson files...')
DEFAULT_FHIR_DIR = "../sample-bulk-fhir-datasets/500-patients/"
# This is a directory containing ndjson files, each with a FHIR resource type, e.g. "AllergyIntolerance.000.ndjson"
# There can be multiple files for each resource type, e.g. "AllergyIntolerance.000.ndjson", "AllergyIntolerance.001.ndjson", etc.
fhir_dir = os.getenv("FHIR_DIR", DEFAULT_FHIR_DIR)
if not os.path.exists(fhir_dir):
    logger.error(f"Directory {fhir_dir} does not exist.")
    exit(1)


logger.info('Creating FHIR cache...')
patient_indexes, line_indexes, unindexed_resources, indexed_resources = parse_fhir_ndjsons(fhir_dir)
logger.info(f'Created indexes for {len(patient_indexes)} fhir resources')
logger.info(f'Unindexed resources: {unindexed_resources}')

bp = Blueprint("fhir_extractor", __name__)

@bp.route("/fhir/<resource_type>/", methods=["POST"])
def get_fhir_resource(resource_type: str):
    resource_type = resource_type.lower()
    offset, limit = FHIRPagination().get_pagination_params()
    filter = request.get_json()
    patients = filter.get('patients', [])
    fields = filter.get('fields', []) # each string is a top-level field to include in the response, e.g. ["id", "status", "code"]
    logger.info(f"Received request for {resource_type} with patients {patients} and fields {fields}")
    if patients:
        if resource_type in unindexed_resources:
            return jsonify('Resource not associated with patients'), 400
        else:
            fhir_response, pagination = get_fhir_resource_for_patients(resource_type, patients, offset, limit)
    else:
        fhir_response, pagination = get_fhir_resource_for_patients(resource_type, patients, offset, limit)
    if fields:
        fhir_response = [filter_fields(resource, fields) for resource in fhir_response]
    return jsonify({
        "fhir": fhir_response,
        "pagination": pagination.to_dict()
    })

def get_fhir_resource_for_patients(resource_type: str, patient_refs: list[str], offset: int, limit: int) -> tuple[list[dict], PaginationObject]:
    resource_type = resource_type.lower()
    logger.info(f"Fetching {resource_type} for patients {patient_refs} (offset={offset}, limit={limit})")

    # Find files whose (lowered) filenames start with the resource_type
    matching_files = [fn for fn in patient_indexes.keys() if fn.lower().startswith(resource_type)]
    if not matching_files:
        pagination = PaginationObject(total=0, count=0, offset=offset, limit=limit)
        return [], pagination

    # Build a deduplicated, ordered list of (filename, line_num) for matching patient refs
    entry_set = set()
    entries: list[tuple[str, int]] = []
    for filename in sorted(matching_files):
        file_index = patient_indexes.get(filename, {})
        if len(patient_refs) == 0:
            for _, line_nums in file_index.items():
                for ln in line_nums:
                    key = (filename, ln)
                    if key not in entry_set:
                        entry_set.add(key)
                        entries.append(key)
        else:
            for pref in patient_refs:
                for ln in file_index.get(pref, []):
                    key = (filename, ln)
                    if key not in entry_set:
                        entry_set.add(key)
                        entries.append(key)

    # Sort entries by filename then line number to produce deterministic ordering
    entries.sort(key=lambda t: (t[0], t[1]))

    total_items = len(entries)
    if total_items == 0:
        pagination = PaginationObject(total=0, count=0, offset=offset, limit=limit)
        return [], pagination

    # Determine which entries fall into the requested page
    page_slice = entries[offset: offset + limit]

    # Group line numbers by filename so we open each file at most once
    files_to_lines: dict[str, set[int]] = {}
    for filename, ln in page_slice:
        files_to_lines.setdefault(filename, set()).add(ln)

    resources: list[dict] = []
    for filename in sorted(files_to_lines.keys()):
        file_path = os.path.join(fhir_dir, filename)
        needed_lines = files_to_lines[filename]
        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f):
                if line_num in needed_lines:
                    line = line.strip()
                    obj = json.loads(line)
                    resources.append(obj)

    items_in_page = len(resources)
    pagination = (FHIRPagination().create_pagination(
        total_items, offset, limit, items_in_page, 'fhir_extractor.get_fhir_resource', resource_type
    ))
    return resources, pagination

def filter_fields(resource: dict, fields: list[str]) -> dict:
    return {field: resource.get(field) for field in fields}


app.register_blueprint(bp)

if __name__ == '__main__':
    app.run(debug=True)

