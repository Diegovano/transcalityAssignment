Assumptions:

You are happy me not checking GPG keys during the sumo-builder installation of sumo

You do not mind me leaving infrastructure which was useful during developement. For example allowing sumo_sim handler to discriminate s3 uris vs paths. My thinking here is that the flexibility allows easier integration into an offline testing pipeline, saving AWS credits (I have no idea how much this stuff costs tbh).

Assuming sumo only produces summary.xml and edge.xml. Other files not cleared during the `finally` step.

Assuming that top 10 busiest does not need to be sorted

Assuming that the output prefix is passed to all other pipeline stages, so all artefacts are stored together.

What I would do with more time:

If I had more time I would make the Dockerfile a little more extentible. Specifically, to add more sumo-tools for instance, we first need to check if its a dynamic executable, in which case we need to copy libs. Otherwise copying the executable is enough.