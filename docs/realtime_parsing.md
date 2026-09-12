# Realtime Parsing And Static Matching

Saved protobuf snapshots are parsed into feed-summary, Trip Update, Stop Time
Update, Vehicle Position, or Service Alert tables. The parser operates on the
immutable raw bytes so a result can be reproduced without another network call.

Compatibility reports compare identifiers with the selected static Silver run.
Unknown identifiers produce explicit warnings; they are not silently coerced
into matches. These tables remain snapshot observations, not historical service
reliability measures.
