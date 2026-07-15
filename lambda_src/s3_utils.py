import os
from pathlib import Path
import shutil

import boto3

import re
import logging
from os import path

import query

logger = logging.getLogger()
logger.setLevel("INFO")
s3 = boto3.client("s3")
paginator = s3.get_paginator("list_objects_v2")

NINE_GIGS_IN_BYTES = 9.5 * 1024 * 1024 * 1024


def prepare_local_data_dir(resource: str) -> bool:
    if query.s3_root:
        # We were seeing significant performance issues when duckdb was reading from S3 directly, so we now download the data to the local /tmp directory first.
        local_dir = Path(path.join(query.local_root, resource))
        # Ugly caching logic to avoid repeat downloads
        if local_dir.exists() and local_dir.is_dir():
            logger.info(
                f"Local directory {local_dir} already exists, skipping download"
            )
            return True
        else:
            shutil.rmtree(query.local_root, ignore_errors=True)

        logger.info("S3_ROOT is set, downloading data from S3")
        bucket, prefix = parse_bucket_and_prefix(f"{query.s3_root}{resource}/")
        logger.info(
            f"Calculating size of S3 objects in bucket: {bucket} with prefix: {prefix}"
        )
        size_bytes = calculate_object_size_bytes(bucket, prefix)
        # Lambda storage limit 10G
        if size_bytes > NINE_GIGS_IN_BYTES:
            logger.error(f"Data size {size_bytes} bytes exceeds 9GB limit")
            return False
        logger.info(f"Data size is {size_bytes} bytes, proceeding to download")
        download_s3_parquets(bucket, prefix, local_dir)
        logger.info(f"Downloaded S3 objects to {local_dir}")
        return True
    return True


def parse_bucket_and_prefix(s3_uri: str) -> tuple[str, str]:
    match = re.match(r"s3://([^/]+)/(.*)", s3_uri)
    if not match:
        logger.error(f"Invalid S3 URI: {s3_uri}")
        raise ValueError(f"Invalid S3 URI: {s3_uri}")
    bucket, prefix = match.groups()
    return bucket, prefix


def calculate_object_size_bytes(bucket_name: str, prefix: str) -> int:
    total_bytes = 0
    page_iterator = paginator.paginate(Bucket=bucket_name, Prefix=prefix)
    for page in page_iterator:
        if "Contents" in page:
            for obj in page["Contents"]:
                total_bytes += obj["Size"]

    return total_bytes


def download_s3_parquets(bucket: str, prefix: str, local_dir: Path) -> None:
    os.makedirs(local_dir, exist_ok=True)

    logger.info(
        f"Downloading S3 objects from bucket: {bucket} path: {prefix} to {local_dir}"
    )

    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            local_path = local_dir / Path(key).name
            local_path.parent.mkdir(parents=True, exist_ok=True)
            s3.download_file(bucket, key, str(local_path))


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


def get_fhir_resource_types() -> list[str]:
    if query.s3_root:
        return list_s3_subdirectories(query.s3_root)
    else:
        return os.listdir(query.local_root)
