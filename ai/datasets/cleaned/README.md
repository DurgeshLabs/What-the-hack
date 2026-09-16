# Bundled demo training replay

`cicids2017_archive_clean.csv` is a 105,000-row normalized replay produced from
the public CICIDS2017 archive variant supplied during project development. It is
included so a fresh clone can train, evaluate pipeline mechanics, upload traffic,
and display a forecast without downloading the 1.7 GB source archive.

It contains the normalized columns used by the application: source/destination
addresses and ports, protocol, timestamp, packets, bytes, duration, flags,
connection information, and label.

The archive variant omitted full hour/day timestamps. The cleaning tool therefore
creates a deterministic source-order replay timeline. This artifact is appropriate
for the local demo and reproducibility checks, but not for publication-quality
accuracy claims. Use original, timestamped CICIDS2017 files for final benchmark
experiments.

SHA-256: `b513721d394229b03816d3010cf120f5f0f20ec7131821f54b9cb1d2331111ca`
