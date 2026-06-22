import re
import pathlib
import zipfile
import shutil
import subprocess
import traceback
from s3helper import s3, parse_s3, TMP
from typing import TypedDict, Any

class SumoSimEvent(TypedDict):
    scenario_zip_url: str
    output_prefix: str


def sumo_sim_handler(event: dict, context: Any):
    edge_output_temp_path = TMP / "edge.xml"
    summary_output_temp_path = TMP / "summary.xml"

    scenario_zip_temp_path = TMP / "scenario.zip"
    scenario_temp_path = TMP / "scenario"

    sumo_sim_event: SumoSimEvent = event

    assert "scenario_zip_url" in sumo_sim_event
    assert "output_prefix" in sumo_sim_event

    url = sumo_sim_event["scenario_zip_url"]
    output_prefix = sumo_sim_event["output_prefix"]
    assert url.endswith(".zip")

    # "final" paths are only used for local testing
    if not output_prefix.startswith("s3://"):
        output_path = pathlib.Path(output_prefix)
        output_path.mkdir(parents=True, exist_ok=True)
        edge_output_final_path = output_path / "edge.xml"
        summary_output_final_path = output_path / "summary.xml"

    try:
        if url.startswith("s3://"):
            bucket, key = parse_s3(url)
            s3.download_file(bucket, key, str(scenario_zip_temp_path))
        else:
            shutil.copy(pathlib.Path(url), scenario_zip_temp_path)

        with zipfile.ZipFile(scenario_zip_temp_path) as zf:
            zf.extractall(scenario_temp_path)

        sumocfg = next(scenario_temp_path.rglob("*.sumocfg"))

        cmd = [
            "sumo",
            "-c",
            str(sumocfg),
            "--edgedata-output",
            str(TMP / "edge.xml"),
            "--summary-output",
            str(TMP / "summary.xml"),
            "--no-warnings",
        ]

        run = subprocess.run(cmd, capture_output=True, text=True)

        try:
            run.check_returncode()
        except subprocess.CalledProcessError:
            print(run.stderr)
            raise

        total_vehicles_matches = re.search(".*TOT (\\d+) ACT", run.stdout)
        total_vehicles_groups = (
            total_vehicles_matches.groups()
            if total_vehicles_matches is not None
            else None
        )

        if total_vehicles_groups is None:
            vehicle_count = -1
        else:
            vehicle_count = int(total_vehicles_groups[0])

        if output_prefix.startswith("s3://"):
            bucket, prefix = parse_s3(output_prefix)

            s3.upload_file(str(edge_output_temp_path), bucket, f"{prefix}/edge.xml")

            s3.upload_file(
                str(summary_output_temp_path), bucket, f"{prefix}/summary.xml"
            )

            return {
                "status": "success",
                "edge_output_url": f"s3://{bucket}/{prefix}/edge.xml",
                "summary_url": f"s3://{bucket}/{prefix}/summary.xml",
                "vehicle_count": vehicle_count,
            }

        else:
            shutil.copy(edge_output_temp_path, edge_output_final_path)
            shutil.copy(summary_output_temp_path, summary_output_final_path)

            return {
                "status": "success",
                "edge_output_url": str(edge_output_final_path),
                "summary_url": str(summary_output_final_path),
                "vehicle_count": vehicle_count,
            }

    except Exception as e:
        raise RuntimeError(f"{e}\n{traceback.format_exc()}") from e
    finally:
        try:
            shutil.rmtree(scenario_temp_path, ignore_errors=True)
            scenario_zip_temp_path.unlink(missing_ok=True)

            # I could also delete the whole tmp dir?
            summary_output_temp_path.unlink(missing_ok=True)
            edge_output_temp_path.unlink(missing_ok=True)
        except:
            pass


if __name__ == "__main__":
    result = sumo_sim_handler(
        SumoSimEvent(scenario_zip_url="test.zip", output_prefix="out/"),
        None,
    )

    print(result)
    if "exception" in result:
        print(result["exception"])
