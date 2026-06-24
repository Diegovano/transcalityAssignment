#!/usr/bin/env python3
import os
import sys
import json
import pathlib
import shutil

# 1. Setup paths so your handler imports resolve correctly
sys.path.append(str(pathlib.Path(__file__).parent.resolve()))

from handlers.sumo_sim import sumo_sim_handler, SumoSimEvent
from handlers.postprocess import postprocess_handler, PostprocessEvent
from handlers.finalise import finalise_handler, FinaliseEvent

def run_local_pipeline(zip_path: str, output_dir: str):
    # Ensure the target local zip file actually exists
    zip_file = pathlib.Path(zip_path).resolve()
    if not zip_file.exists():
        print(f"Error: Could not find scenario file at '{zip_file}'")
        sys.exit(1)

    # Clean out older test targets
    output_prefix = str(pathlib.Path(output_dir).resolve()) + "/"
    shutil.rmtree(output_prefix, ignore_errors=True)
    
    print("--- STEP 1: Running SUMO Simulation ---")
    sumo_sim_event = SumoSimEvent(
        scenario_zip_url=str(zip_file),
        output_prefix=output_prefix
    )
    
    # Run the simulation handler (Context argument mocked as None)
    sumo_sim_response = sumo_sim_handler(sumo_sim_event, None)
    
    print(f"Simulation Succeeded! Total vehicles: {sumo_sim_response['vehicle_count']}")
    print(f"Generated {len(sumo_sim_response['intervals'])} analysis intervals.")

    print("\n--- STEP 2: Running Fanout Postprocessing ---")
    postprocess_responses = []

    for i, interval in enumerate(sumo_sim_response["intervals"]):
        print(f" Processing interval {i+1}/{len(sumo_sim_response['intervals'])}: {interval}")
        
        postprocess_event = PostprocessEvent(
            edge_output_url=sumo_sim_response["edge_output_url"],
            output_prefix=output_prefix,
            interval=interval
        )

        postprocess_response = postprocess_handler(postprocess_event, None)
        postprocess_responses.append(postprocess_response)

    print("\n--- STEP 3: Running Pipeline Finalization ---")
    finalise_event = FinaliseEvent(
        parquet_urls=list(map(lambda res: res["parquet_url"], postprocess_responses)),
        output_prefix=output_prefix
    )

    finalise_response = finalise_handler(finalise_event, None)
    
    print("\n==============================================")
    print("PIPELINE STATUS: SUCCESS")
    print(f"Final output logs: {finalise_response['summary_url']}")
    print("==============================================")

if __name__ == "__main__":
    # Point these to your downloaded files or pass them as CLI arguments
    SCENARIO_ZIP = "small-scenario.zip" 
    OUTPUT_DIRECTORY = "out"

    # Allow custom arguments from terminal if wanted
    if len(sys.argv) > 1:
        SCENARIO_ZIP = sys.argv[1]
    if len(sys.argv) > 2:
        OUTPUT_DIRECTORY = sys.argv[2]

    run_local_pipeline(SCENARIO_ZIP, OUTPUT_DIRECTORY)