import json
import pathlib
import shutil
import polars as pl
import xml.etree.ElementTree as ET
import traceback
from s3helper import s3, parse_s3, TMP
from typing import TypedDict, Any
from urllib.parse import urlparse

class PostprocessEvent(TypedDict):
    edge_output_url: str
    output_prefix: str


def postprocess_handler(event: dict, context: Any):
    """CloudWatch shows MaxMemoryUsed of ~148 MB against
    an allocation of 512 MB. Could safely be reduced to
    256 MB. First init time is high (~6s) later invocations 
    run in ~300-450ms"""
    edge_output_temp_path = TMP / "edge_output.xml"
    parquet_temp_path = TMP / "edges.parquet"

    postprocess_event: PostprocessEvent = event

    assert "edge_output_url" in postprocess_event
    assert "output_prefix" in postprocess_event

    url = postprocess_event["edge_output_url"]
    output_prefix = postprocess_event["output_prefix"]

    if not output_prefix.startswith("s3://"):
        output_path = pathlib.Path(output_prefix)
        output_path.mkdir(parents=True, exist_ok=True)
        parquet_final_path = output_path / "edges.parquet"

    try:
        if url.startswith("s3://"):
            bucket, key = parse_s3(url)
            s3.download_file(bucket, key, str(edge_output_temp_path))
        else:
            original_path = pathlib.Path(url)
            shutil.copy(original_path, edge_output_temp_path)

        current_interval_begin: float | None = None
        rows: list[dict[str, str | float]] = []

        # See note about exporting directly as .parquet in README
        for xml_event, elem in ET.iterparse(edge_output_temp_path, ("start", "end")):
            if xml_event == "start" and elem.tag == "interval":
                current_interval_begin = float(elem.attrib["begin"])
            elif (
                xml_event == "end"
                and elem.tag == "edge"
                and current_interval_begin is not None
            ):
                row = {
                    "interval_begin": current_interval_begin,
                    "edge_id": elem.attrib["id"],
                    "speed": float(elem.attrib["speed"]),
                    "density": float(elem.attrib["density"]),
                    "flow": float(elem.attrib["flow"]),
                    "waiting_time": float(elem.attrib["waitingTime"]),
                    "sampled_seconds": float(elem.attrib["sampledSeconds"])
                }
                elem.clear()

                rows.append(row)

        df = pl.DataFrame(rows)
        df.lazy().sort(["interval_begin", "edge_id"]).sink_parquet(parquet_temp_path)

        if output_prefix.startswith("s3://"):
            bucket, prefix = parse_s3(output_prefix)

            s3.upload_file(str(parquet_temp_path), bucket, f"{prefix}/edges.parquet")

            return {
                "status": "success",
                "parquet_url": f"s3://{bucket}/{prefix}/edges.parquet",
                "rows": df.height,
            }
        else:
            shutil.copy(parquet_temp_path, parquet_final_path)

            return {
                "status": "success",
                "parquet_url": str(parquet_final_path),
                "rows": df.height,
            }

    except Exception as e:
        raise RuntimeError(f"{e}\n{traceback.format_exc()}") from e
    finally:
        try:
            edge_output_temp_path.unlink(missing_ok=True)
            parquet_temp_path.unlink(missing_ok=True)
        except:
            pass


if __name__ == "__main__":
    result = postprocess_handler(
        json.dumps(PostprocessEvent(edge_output_url="test.zip")),
        None,
    )

    print(result)
    if "exception" in result:
        print(result["exception"])
