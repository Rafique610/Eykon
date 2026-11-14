# Route R4 CSVs (EYKO-108)

Raw files from the Infinix X670, 8 Nov 2026, pulled unedited from the phone. See `docs/results/2026-11-08-route-r4-static.md`.

**Do not plot the `*-fullrank-*` files.** Their rows (`sqlite_vec_static-full-ranking`) time queries that **returned 0 rows**:
sqlite-vec refuses `LIMIT` above 4,096 ("k value in knn query too large"), so the milliseconds are the time of a failed query, and the
note column says "0 rows returned". They are kept as evidence of the 4,096-row limit, not as speeds. The speed rows are in the
`eyko108-r4-neon-*`, `eyko108-r4-noneon-*` and `eyko108-r4-memory-neon-*` files (the `-0256` neon file was an entirely plugged-in
flight-mode run; `-0320` is the unplugged one).
