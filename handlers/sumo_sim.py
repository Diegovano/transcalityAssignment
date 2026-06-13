import json
import re
import pathlib
import zipfile
import shutil
import subprocess
import traceback
from typing import TypedDict, Any


class SumoSimEvent(TypedDict):
    scenario_zip_url: str
    output_prefix: str


def sumo_sim_handler(event: str, context: Any):
    try:
        sumo_sim_event: SumoSimEvent = json.loads(event)

        for key in sumo_sim_event.keys():
            assert key in sumo_sim_event

        url = sumo_sim_event["scenario_zip_url"]
        output_prefix = pathlib.Path(sumo_sim_event["output_prefix"])
        assert url.endswith(".zip")

        temp_path_zip = pathlib.Path("tmp/scenario.zip")
        temp_path = pathlib.Path("tmp/scenario")

        if url.startswith("s3://"):
            pass
        else:
            original_path = pathlib.Path(url)
            shutil.copy(original_path, temp_path_zip)

        with zipfile.ZipFile(temp_path_zip) as zf:
            zf.extractall(temp_path)

        sumocfg = next(temp_path.rglob("*.sumocfg"))

        cmd = [
            "sumo",
            "-c",
            str(sumocfg),
            "--edgedata-output",
            "tmp/edge.xml",
            "--summary-output",
            "tmp/summary.xml",
            "--no-warnings",
        ]

        run = subprocess.run(cmd, capture_output=True)
        print(run.stderr.decode())
         
        total_vehicles_regex = re.compile(".*TOT (\\d+) ACT")
        total_vehicles_matches = total_vehicles_regex.match(run.stdout.decode())
        total_vehicles_groups = (
            total_vehicles_matches.groups()
            if total_vehicles_matches is not None
            else None
        )

        if total_vehicles_groups is None:
            vehicle_count = -1
        else:
            vehicle_count = int(total_vehicles_groups[0])

        if url.startswith("s3://"):
            pass
        else:
            edge_output_temp_path = pathlib.Path("tmp/edge.xml")
            edge_output_final_path = output_prefix / "edge.xml"
            summary_output_temp_path = pathlib.Path("tmp/summary.xml")
            summary_output_final_path = output_prefix / "summary.xml"

            shutil.copy(edge_output_temp_path, edge_output_final_path)
            shutil.copy(summary_output_temp_path, summary_output_final_path)

        return {
            "status": "success",
            "edge_output_url": edge_output_final_path,
            "summary_url": summary_output_final_path,
            "vehicle_count": vehicle_count,
        }

    except Exception as e:
        return {
            "status": "failed",
            "exception": f"{e}\n{traceback.format_exc()}",  # I don't think an Exception is serialisable
        }
    finally:
        shutil.rmtree("tmp/scenario", ignore_errors=True)
        pathlib.Path("tmp/scenario.zip").unlink(missing_ok=True)
        
        # I could also delete the whole tmp dir?
        pathlib.Path("tmp/summary.xml").unlink(missing_ok=True)
        pathlib.Path("tmp/edge.xml").unlink(missing_ok=True)


if __name__ == "__main__":
    result = sumo_sim_handler(
        json.dumps(SumoSimEvent(scenario_zip_url="test.zip", output_prefix="out/")),
        None,
    )

    print(result)
    if "exception" in result:
        print(result["exception"])
