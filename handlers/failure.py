import json
import datetime
from s3helper import s3
from typing import TypedDict, Any

BUCKET = "transcality-intern"

class FailureEvent(TypedDict):
    execution_id: str | None
    error: Any

def failure_handler(event: dict, context: Any) -> dict:
    failure_event: FailureEvent = event

    execution_id = (
        failure_event.get("execution_id")
        or getattr(context, "aws_request_id", None)
        or "unknown"
    )

    error = event.get("error", {})

    error_payload = {
        "execution_id": execution_id,
        "timestamp": datetime.utcnow().isoformat(),
        "error": {
            "type": error.get("Error"),
        } if isinstance(error, dict) else str(error),
    }

    key = f"diego-van-overberghe/errors/{execution_id}.json"

    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=json.dumps(error_payload).encode("utf-8"),
        ContentType="application/json",
    )

    return {"status": "failed", "error_url": f"s3://{BUCKET}/{key}"}
