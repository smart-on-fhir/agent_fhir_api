import os
import re

import boto3
import duckdb
import logging
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger("INFO")

template_env = Environment(
    loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates")),
    trim_blocks=True,
    lstrip_blocks=True,
)

PATH_NOT_SET = "NOT SET"
s3_root = os.getenv("S3_ROOT")
local_root = os.getenv("LOCAL_ROOT")
fhir_data_path = s3_root if s3_root else (local_root if local_root else PATH_NOT_SET)

s3 = boto3.client("s3")


def create_s3_based_db_con() -> duckdb.DuckDBPyConnection:
    session = boto3.session.Session()  # type: ignore
    credentials = session.get_credentials().get_frozen_credentials()
    logger.info("Creating duckdb connection")
    con = duckdb.connect(":memory:")
    logger.info("Setting up s3 query config")
    con.execute("INSTALL httpfs;")
    con.execute("LOAD httpfs;")
    con.execute("SET s3_region='us-east-1';")
    con.execute(f"SET s3_access_key_id='{credentials.access_key}';")
    con.execute(f"SET s3_secret_access_key='{credentials.secret_key}';")
    con.execute(f"SET s3_session_token='{credentials.token}';")
    return con


def create_local_db_con() -> duckdb.DuckDBPyConnection:
    logger.info("Creating duckdb connection")
    return duckdb.connect(":memory:")


def get_fhir_data(
    con: duckdb.DuckDBPyConnection,
    resource: str,
    fields: list[str],
    patients: list[str],
    offset: int,
    limit: int,
):
    logger.info("Setting up query")
    parquet_pattern = fhir_data_path + resource + "/*"
    if resource != "patient":
        patients = [f"Patient/{p}" for p in patients] if patients else []

    template = template_env.get_template("fhir_query.sql.jinja2")
    query = template.render(
        has_fields=bool(fields),
        has_patients=bool(patients),
        patient_path=get_patient_path(resource),
    )

    if fields and patients:
        logger.info("Fetching data, filtering fields and patients")
        params = [fields, parquet_pattern, patients]
    elif fields:
        logger.info("Fetching data, filtering fields")
        params = [fields, parquet_pattern, limit, offset]
    elif patients:
        logger.info("Fetching data, filtering patients")
        params = [parquet_pattern, patients, limit, offset]
    else:
        logger.info("Fetching data, no filtering")
        params = [parquet_pattern, limit, offset]

    result = con.execute(query, params).fetchall()
    column_names = [desc[0] for desc in con.description]
    return [to_dict(row, column_names) for row in result]


def to_dict(row: tuple, column_names: list[str]):
    obj = {}
    for i, cell in enumerate(row):
        obj[column_names[i]] = cell
    return obj


def get_fhir_count(
    con: duckdb.DuckDBPyConnection, resource: str, patients: list[str]
) -> int:
    parquet_pattern = os.path.join(fhir_data_path, resource, "*")

    template = template_env.get_template("fhir_count.sql.jinja2")
    query = template.render(
        has_patients=bool(patients),
        patient_path=get_patient_path(resource),
    )

    if patients:
        params = [parquet_pattern, patients]
    else:
        params = [parquet_pattern]

    result = con.execute(query, params).fetchall()
    return result[0][0]


def get_patient_path(resource: str) -> str:
    resource_map = {
        "allergyintolerance": "patient.reference",
        "device": "patient.reference",
        "diagnosticreport": "subject.reference",
        "documentreference": "subject.reference",
        "encounter": "subject.reference",
        "episodeofcare": "patient.reference",
        "immunization": "patient.reference",
        "medicationdispense": "patient.reference",
        "medicationrequest": "subject.reference",
        "patient": "id",
    }
    return resource_map.get(resource.lower(), "subject.reference")


def get_fhir_resource_types() -> list[str]:
    if s3_root:
        return list_s3_subdirectories(s3_root)
    else:
        return os.listdir(local_root)


def list_s3_subdirectories(s3_uri: str) -> list[str]:
    match = re.match(r"s3://([^/]+)/(.*)", s3_uri)
    if not match:
        return []
    bucket_name = match.group(1)
    prefix = match.group(2)
    if prefix and not prefix.endswith("/"):
        prefix += "/"

    subdirectories = []

    logger.info(f"Scanning S3 subdirectories under: s3://{bucket_name}/{prefix}")
    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(
        Bucket=bucket_name,
        Prefix=prefix,
        Delimiter="/",  # Tells S3 to roll up everything past this slash into CommonPrefixes
    )
    for page in pages:
        if "CommonPrefixes" in page:
            for cp in page["CommonPrefixes"]:
                folder_path = cp["Prefix"]
                # Strip out the parent prefix to return just the relative directory name
                relative_dir = folder_path[len(prefix) :]
                subdirectories.append(relative_dir.replace("/", ""))

    return subdirectories
