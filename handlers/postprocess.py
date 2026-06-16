import json
import re
import pathlib
import zipfile
import shutil
import polars as pl
import xml.etree.ElementTree as ET
import traceback
from typing import TypedDict, Any

class PostprocessEvent(TypedDict):
    edge_output_url: str

def postprocess_handler(event: dict, context: Any):
    try:
        postprocess_event: PostprocessEvent = json.loads(event)
        assert "edge_output_url" in postprocess_event

        url = postprocess_event["edge_output_url"]
        edge_output_temp_path = pathlib.Path("tmp/edge_output.xml")
        
        if url.startswith("s3://"):
            pass
        else:
            original_path = pathlib.Path(url)
            shutil.copy(original_path, edge_output_temp_path)

        current_interval_begin: float | None = None
        rows: list[dict[str, str | float]] = []

        for (xml_event, elem) in ET.iterparse(edge_output_temp_path, ("start", "end")):
            if xml_event == "start" and elem.tag == "interval":
                current_interval_begin = float(elem.attrib["begin"])
            elif xml_event == "end" and elem.tag == "edge" and current_interval_begin is not None:
                row = {
                    "interval_begin": current_interval_begin,
                    "edge_id": elem.attrib["id"],
                    "speed": float(elem.attrib["speed"]),
                    "density": float(elem.attrib["density"]),
                    "flow": float(elem.attrib["flow"]),
                    "waiting_time": float(elem.attrib["waitingTime"]),
                }
                elem.clear()

                rows.append(row)

        df = pl.DataFrame(rows)
        parquet_temp_path = pathlib.Path("tmp/edges.parquet")
        df.lazy().sort(["interval_begin", "edge_id"]).sink_parquet(parquet_temp_path)

        if url.startswith("s3://"):
            pass
        else:
            return {"parquet_url": str(parquet_temp_path), "rows": df.height}

    except Exception as e:
        return {
            "status": "failed",
            "exception": f"{e}\n{traceback.format_exc()}",  # I don't think an Exception is serialisable
        }
    finally:
        try:
            pass
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
