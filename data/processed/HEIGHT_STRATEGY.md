\# Building height enrichment (Dallas CBD 4km)



Study area: 4 km × 4 km square centered on Downtown Dallas (CBD).



Height assignment priority for each building:

1\) Use OpenStreetMap height tags when present (height or building:height), parsed to meters.

2\) Else use building:levels × 3.2 m per level.

3\) Else assign a footprint-area-based randomized height with a small tall-building tail so downtown includes a realistic mix of low-, mid-, and high-rise buildings.



Quality report (latest run):

\- n = 1553 buildings

\- 10.1739% OSM height tags

\- 13.2003% levels-derived

\- 76.6259% randomized fallback

\- median = 22.0803 m, max = 300.0 m



Canonical output dataset:

\- data/processed/dallas\_cbd\_4000m\_osm\_buildings\_height.gpkg

Plus:

\- data/processed/dallas\_cbd\_4000m\_osm\_buildings\_height\_quality.csv

\- data/processed/dallas\_cbd\_4000m\_osm\_buildings\_height\_hist.png



