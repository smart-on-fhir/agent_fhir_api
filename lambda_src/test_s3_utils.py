import boto3

from moto import mock_aws


def test_list_s3_subdirectories_returns_top_level_directories():
    # function scoped imports needed to stop s3 from exploding
    from lambda_src import s3_utils

    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="example-bucket")
        s3.put_object(
            Bucket="example-bucket", Key="resource-a/file1.parquet", Body=b"1"
        )
        s3.put_object(
            Bucket="example-bucket", Key="resource-b/file2.parquet", Body=b"2"
        )
        s3.put_object(Bucket="example-bucket", Key="README.txt", Body=b"3")

        result = s3_utils.list_s3_subdirectories("s3://example-bucket/")

        assert sorted(result) == ["resource-a", "resource-b"]


def test_should_calculate_total_size_of_objects():
    from lambda_src import s3_utils

    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="example-bucket")
        s3.put_object(Bucket="example-bucket", Key="prefix/file1.parquet", Body=b"abc")
        s3.put_object(
            Bucket="example-bucket", Key="prefix/file2.parquet", Body=b"defgh"
        )

        total_size = s3_utils.calculate_object_size_bytes("example-bucket", "prefix/")

        assert total_size == 8


def test_should_download_s3_objects_to_local_dir(tmp_path):
    from lambda_src import s3_utils

    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="example-bucket")
        s3.put_object(Bucket="example-bucket", Key="prefix/file1.parquet", Body=b"abc")
        s3.put_object(
            Bucket="example-bucket", Key="prefix/file2.parquet", Body=b"defgh"
        )

        s3_utils.download_s3_parquets("example-bucket", "prefix/", tmp_path)

        assert (tmp_path / "file1.parquet").read_bytes() == b"abc"
        assert (tmp_path / "file2.parquet").read_bytes() == b"defgh"


def test_should_parse_bucket_and_prefix():
    from lambda_src import s3_utils

    with mock_aws():
        bucket, prefix = s3_utils.parse_bucket_and_prefix("s3://my-bucket/my-prefix/")
        assert bucket == "my-bucket"
        assert prefix == "my-prefix/"


def test_should_parse_bucket_and_prefix_without_trailing_slash():
    from lambda_src import s3_utils

    with mock_aws():
        bucket, prefix = s3_utils.parse_bucket_and_prefix(
            "s3://another-bucket/another-prefix"
        )
        assert bucket == "another-bucket"
        assert prefix == "another-prefix"


def test_should_raise_value_error_for_invalid_s3_uri():
    from lambda_src import s3_utils
    import pytest

    with pytest.raises(ValueError), mock_aws():
        s3_utils.parse_bucket_and_prefix("invalid-uri")
