import boto3
import os
from pathlib import Path
from urllib.parse import urlparse

s3 = boto3.client("s3")

def parse_s3(url: str):
    assert url.startswith("s3://")
    p = urlparse(url)
    return p.netloc, p.path.lstrip("/")

IS_LAMBDA = "AWS_LAMBDA_FUNCTION_NAME" in os.environ

TMP = Path("/tmp") if IS_LAMBDA else Path("tmp")
TMP.mkdir(exist_ok=True)
