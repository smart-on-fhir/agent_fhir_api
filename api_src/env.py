import os

source_bucket = os.getenv("SOURCE_BUCKET", "")
local_root = os.getenv("LOCAL_ROOT", "/tmp/fhir_data/")


def uses_s3() -> bool:
    return source_bucket != ""
