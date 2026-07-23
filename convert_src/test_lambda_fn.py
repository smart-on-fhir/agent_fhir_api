import os
import shutil

from convert_src import lambda_fn


def test_should_convert_local_json(tmp_path):
    source_file = os.path.join(tmp_path, "Patient.000.ndjson")
    output_file = os.path.join(tmp_path, "Patient.000.parquet")
    shutil.copy("./test_data/my_json_cohort/patient/Patient.000.ndjson", source_file)
    event = {"Records": [{"s3": {"object": {"key": source_file}}}]}
    lambda_fn.lambda_handler(event, None)

    assert os.path.isfile(output_file), f"File not found at: {output_file}"
    assert not os.path.exists(source_file), f"File not deleted: {source_file}"
