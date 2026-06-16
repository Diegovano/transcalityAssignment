import json
import re
import pathlib
import zipfile
import shutil
import polars as pl
import xml.etree.ElementTree as ET
import traceback
from typing import TypedDict, Any

class FinaliseEvent(TypedDict):
    parquet_url: str

def finalise_handler(event: dict, context: Any):
    try:
        finalise_event: FinaliseEvent = json.loads(event)
        assert "parquet_url" in finalise_event

        url = finalise_event["parquet_url"]
        parquet_temp_path = pathlib.Path("tmp/edges.parquet")
        
        if url.startswith("s3://"):
            pass
        else:
            original_path = pathlib.Path(url)
            shutil.copy(original_path, parquet_temp_path)

        df = pl.scan_parquet(parquet_temp_path)
        max_flow_top_10_lf = (
            df
            .group_by("edge_id")
            .agg(pl.col("flow").sum().alias("total_flow"))
            .top_k(k=10, by="total_flow")
        )
        global_mean_speed_lf = (
            df
            .select(pl.col("speed").mean().alias("global_mean_speed"))
        )
        total_sim_time_lf = (
            df
            .select(pl.col("sampledSeconds").sum().alias("total_sim_time"))
        )

        max_flow_top_10, global_mean_speed, total_sim_time = (
            pl.collect_all([
                max_flow_top_10_lf,
                global_mean_speed_lf,
                total_sim_time_lf
            ])
        )

        if url.startswith("s3://"):
            pass
        else:
            return json.dumps({
                "status": "success",
                "top_10_busiest_edges_by_total_flow": max_flow_top_10.collect()["edge_id"].to_list(),
                "global_mean_speed": global_mean_speed.collect().item(),
                "total_simulated_veh_time": total_sim_time.collect().item()
            })

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
    result = finalise_handler(
        json.dumps(FinaliseEvent(parquet_url="testedges.parquet")),
        None,
    )

    print(result)
    if "exception" in result:
        print(result["exception"])
