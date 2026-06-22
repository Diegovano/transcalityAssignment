import json
import pathlib
import shutil
import polars as pl
import traceback
from s3helper import s3, parse_s3, TMP
from typing import TypedDict, Any

class FinaliseEvent(TypedDict):
    parquet_url: str
    output_prefix: str


def finalise_handler(event: dict, context: Any) -> dict:
    """CloudWatch shows MaxMemoryUsed of ~150 MB against
    an allocation of 512 MB. Could safely be reduced to
    256 MB. First init time ~800ms-1.3s. 
    Later invocations run in ~400-550ms."""
    parquet_temp_path = TMP / "edges.parquet"

    finalise_event: FinaliseEvent = event
    assert "parquet_url" in finalise_event
    assert "output_prefix" in finalise_event

    url = finalise_event["parquet_url"]
    output_prefix = finalise_event["output_prefix"]

    if not output_prefix.startswith("s3://"):
        output_path = pathlib.Path(output_prefix)
        output_path.mkdir(parents=True, exist_ok=True)
        summary_json_final_path = output_path / "summary.json"

    try:
        if url.startswith("s3://"):
            bucket, key = parse_s3(url)
            s3.download_file(bucket, key, str(parquet_temp_path))
        else:
            shutil.copy(pathlib.Path(url), parquet_temp_path)

        df = pl.scan_parquet(parquet_temp_path)
        max_flow_top_10_lf = (
            df.group_by("edge_id")
            .agg(pl.col("flow").sum().alias("total_flow"))
            .top_k(k=10, by="total_flow")
        )
        global_mean_speed_lf = df.select(
            pl.col("speed").mean().alias("global_mean_speed")
        )
        total_sim_time_lf = df.select(
            pl.col("sampled_seconds").sum().alias("total_sim_time")
        )

        max_flow_top_10, global_mean_speed, total_sim_time = pl.collect_all(
            [max_flow_top_10_lf, global_mean_speed_lf, total_sim_time_lf]
        )

        summary_json = json.dumps({
                "top_10_busiest_edges_by_total_flow": max_flow_top_10[
                    "edge_id"
                ].to_list(),
                "global_mean_speed": global_mean_speed.item(),
                "total_simulated_veh_time": total_sim_time.item(),
            })

        if output_prefix.startswith("s3://"):
            bucket, prefix = parse_s3(output_prefix)

            s3.put_object(Bucket=bucket, Key=f"{prefix}/summary.json", Body=summary_json.encode())

            return {
                "status": "success",
                "summary_url": f"s3://{bucket}/{prefix}/summary.json"
            }
        else:
            with open(summary_json_final_path, "w", encoding="utf-8") as f:
                f.write(summary_json)

            return {
                "status": "success",
                "summary_url": str(summary_json_final_path)
            }

    except Exception as e:
        raise RuntimeError(f"{e}\n{traceback.format_exc()}") from e
    finally:
        try:
            parquet_temp_path.unlink(missing_ok=True)
        except:
            pass


if __name__ == "__main__":
    result = finalise_handler(
        json.dumps(FinaliseEvent(parquet_url="testedges.parquet")),
        None,
    )

    print(result)
    if "exception" in result:
        print(result["exception"])
