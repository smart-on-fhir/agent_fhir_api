import logging
import os
import re
import duckdb
import boto3
from urllib.parse import urlparse, unquote_plus


logger = logging.getLogger()
logger.setLevel("INFO")

s3 = boto3.client("s3")


def lambda_handler(event, context):
    for record in event["Records"]:
        bucket_name = record["s3"].get("bucket", {}).get("name", "")
        raw_key = record["s3"]["object"]["key"]
        object_key = unquote_plus(raw_key)

        uses_s3 = bucket_name != ""
        source = f"s3://{bucket_name}/{object_key}" if uses_s3 else raw_key
        destination = re.sub(r"ndjson$", "parquet", source)
        logger.info(f"Converting json in {source} to parquet in {destination}")
        if uses_s3:
            con = create_s3_based_db_con()
            logger.info("Credentials created. Converting...")
        else:
            con = duckdb.connect(":memory:")
            logger.info("No s3 detected in src/dest, using local db")

        convert_json(source, destination, con)
        delete_json(source, uses_s3)
    logger.info("Done :)")


def delete_json(path: str, in_s3: bool):
    if in_s3:
        parsed_url = urlparse(path)
        bucket = parsed_url.netloc
        key = parsed_url.path.lstrip("/")
        logger.info(f"Deleting old json in bucket {bucket} at {key}")
        s3.delete_object(Bucket=bucket, Key=key)
    else:
        logger.info(f"Deleting old json {path}")
        os.remove(path)


def convert_json(source: str, destination: str, con: duckdb.DuckDBPyConnection):
    logger.info(f"Converting json {source} to {destination}")
    query = """
        COPY (
            SELECT * 
            FROM read_ndjson_auto(?, union_by_name=true)
        ) 
        TO ? 
        (
            FORMAT PARQUET, 
            COMPRESSION 'zstd'
        );
        """
    con.execute(query, [destination, source])


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
