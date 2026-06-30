import argparse
import math

import logging
import json

import query

logger = logging.getLogger("INFO")


def lambda_handler(event, context):
    if query.fhir_data_path == query.PATH_NOT_SET:
        logger.error("S3_ROOT and LOCAL_ROOT not set")
        return {"statusCode": 500, "body": "Lambda misconfigured. See logs."}
    elif query.s3_root:
        con = query.create_s3_based_db_con()
    else:
        con = query.create_local_db_con()
    logger.info("Created connection")
    resource, fields, patients, offset, limit = extract_params(event)
    resources = query.get_fhir_resource_types()
    logger.info(f"Found the following resources: {resources}")
    if resource in resources:
        data = query.get_fhir_data(con, resource, fields, patients, offset, limit)
        count = query.get_fhir_count(con, resource, patients)
        con.close()
        resources.remove(resource)
        body = {
            "fhir": data,
            "pagination": {
                "count": math.ceil(count / limit),
                "first": f"/fhir/{resource}/?_offset=0&limit={limit}",
                "last": f"/fhir/{resource}/?_offset={math.floor(count / limit) * limit}&limit={limit}",
                "limit": limit,
                "next": f"/fhir/{resource}/?_offset={offset + limit}&limit={limit}",
                "offset": offset,
                "previous": f"/fhir/{resource}/?_offset={max(offset - limit, 0)}&limit={limit}",
                "total": count,
            },
            "otherResources": resources,
        }
        return {"statusCode": 200, "body": json.dumps(body)}
    else:
        return {
            "statusCode": "404",
            "body": f"Resource {resource} not found",
        }


def extract_params(event) -> tuple[str, list[str], list[str], int, int]:
    resource = event.get("pathParameters").get("fhir_resource")
    fields = []
    patients = []
    offset = 0
    limit = 50
    if event.get("body"):
        body = json.loads(event.get("body"))
        fields = body.get("fields", [])
        patients = body.get("patients", [])
    if event.get("queryStringParameters"):
        offset = int(event.get("queryStringParameters").get("offset", "0"))
        limit = int(event.get("queryStringParameters").get("limit", "50"))
    return resource, fields, patients, offset, limit


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run FHIR Lambda handler from CLI")
    parser.add_argument("--fhir_resource", required=True, help="FHIR resource type")
    parser.add_argument("--body", required=True, help="JSON string body")
    parser.add_argument("--limit", default="50", help="Pagination limit")
    parser.add_argument("--offset", default="0", help="Pagination offset")
    args = parser.parse_args()

    event = {
        "pathParameters": {"fhir_resource": args.fhir_resource},
        "queryStringParameters": {"offset": args.offset, "limit": args.limit},
        "body": args.body,
    }
    print(lambda_handler(event, None))
