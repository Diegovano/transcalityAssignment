import re
import pathlib
import zipfile
import shutil
import subprocess
import traceback
from s3helper import s3, parse_s3, TMP
from typing import TypedDict, Any
import xml.etree.ElementTree as ET

class Interval(TypedDict):
    begin: float
    end: float

class SumoSimEvent(TypedDict):
    scenario_zip_url: str
    output_prefix: str
    intervals: list[Interval]


def sumo_sim_handler(event: dict, context: Any):
    """This lambda failed with the default 
    AWS settings. (3s timeout 128 MB mem)
    I then greatly increased these, to
    300s timeout and 1024 MB of memory.
    CloudWatch indicates approximately 7s 
    execution time, and approx 210 MB mem.
    The failure can therefore be linked to 
    the timeout and the higher mem usage.
    Although we could optimise, it might 
    be advisable to not for example lower 
    MaxMem to 256 MB, which could still 
    run the small scenario. Leaving a higher 
    allowance accommodates potentially 
    larger scenarios. This is true for other 
    lambdas also, so I will not repeat this.
    At the same time, I premeptively increased 
    other lambdas' allowances."""
    INTERVAL_SIZE = 300

    edge_output_temp_path = TMP / "edge.xml"
    absolute_edge_output_path = str(edge_output_temp_path.resolve())

    summary_output_temp_path = TMP / "summary.xml"

    scenario_zip_temp_path = TMP / "scenario.zip"
    scenario_temp_path = TMP / "scenario"

    edge_period_add_xml_temp_path = TMP / "edge_period.add.xml"

    edge_period_add_xml_temp_path.write_text(
        """<additional><edgeData id="split_periods" """ +
        f"""file="{absolute_edge_output_path}" freq="{INTERVAL_SIZE}"/>""" +
        """</additional>""".strip())

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
            "--summary-output",
            str(summary_output_temp_path),
            "--no-warnings",
            "--additional-files", # This will force SUMO to break up the edge aggreagation into 300s intervals
            str(edge_period_add_xml_temp_path),
        ]

        run = subprocess.run(cmd, capture_output=True, text=True)

        try:
            run.check_returncode()
        except subprocess.CalledProcessError:
            print(run.stderr)
            raise

        total_time_and_total_vehicle_matches = (
            re.search(".*#(\\d+(?:\\.\\d+)?).*TOT (\\d+) ACT", run.stdout)
        )
        total_time_and_total_vehicle_groups = (
            total_time_and_total_vehicle_matches.groups()
            if total_time_and_total_vehicle_matches is not None
            else None
        )

        if total_time_and_total_vehicle_groups is None:
            # total_time = 0
            vehicle_count = -1
            # intervals = []
        else:
            # total_time = ceil(float(total_time_and_total_vehicle_groups[0]))
            vehicle_count = int(total_time_and_total_vehicle_groups[1])

            # full_intervals = total_time // INTERVAL_SIZE
            # intervals = [{"begin": i*INTERVAL_SIZE, "end": (i+1)*INTERVAL_SIZE} for i in range(full_intervals)]
            # if full_intervals != total_time / INTERVAL_SIZE:
            #     intervals.append({"begin": full_intervals * INTERVAL_SIZE, "end": total_time})

        intervals = []

        for _, elem in ET.iterparse(edge_output_temp_path, events=("end",)):
            if elem.tag == "interval":
                intervals.append({
                    "begin": float(elem.attrib["begin"]),
                    "end": float(elem.attrib["end"])
                })
                elem.clear()

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
                "intervals": intervals
            }

        else:
            shutil.copy(edge_output_temp_path, edge_output_final_path)
            shutil.copy(summary_output_temp_path, summary_output_final_path)

            return {
                "status": "success",
                "edge_output_url": str(edge_output_final_path),
                "summary_url": str(summary_output_final_path),
                "vehicle_count": vehicle_count,
                "intervals": intervals
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

            edge_period_add_xml_temp_path.unlink(missing_ok=True)
            pass
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
