from handlers.sumo_sim import sumo_sim_handler, SumoSimEvent
from handlers.postprocess import postprocess_handler, PostprocessEvent
from handlers.finalise import finalise_handler, FinaliseEvent
from handlers.failure import failure_handler, FailureEvent


def test_contracts_and_pipeline():
    output_prefix = "test_out/"

    sumo_sim_event = SumoSimEvent(
        scenario_zip_url="test_data/test.zip",
        output_prefix=output_prefix
    )

    sumo_sim_response = sumo_sim_handler(sumo_sim_event, None)

    assert "status" in sumo_sim_response
    assert "edge_output_url" in sumo_sim_response
    assert "summary_url" in sumo_sim_response
    assert "vehicle_count" in sumo_sim_response

    postprocess_event = PostprocessEvent(
        edge_output_url=sumo_sim_response["edge_output_url"],
        output_prefix=output_prefix
    )

    postprocess_response = postprocess_handler(postprocess_event, None)

    assert "status" in postprocess_response
    assert "parquet_url" in postprocess_response
    assert "rows" in postprocess_response

    finalise_event = FinaliseEvent(
        parquet_url=postprocess_response["parquet_url"],
        output_prefix=output_prefix
    )

    finalise_response = finalise_handler(finalise_event, None)

    assert "status" in finalise_response
    assert "summary_url" in finalise_response

