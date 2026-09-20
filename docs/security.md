# Scoped Operator Security

Incident reads require `operations:read`, mutations require `incidents:write`,
and manual evaluation requires `admin`. Tokens contain a subject, scopes, and an
expiry, and are signed with HMAC-SHA256 using `MCT_AUTH_SECRET`.

This is a small project-specific bearer format. It is not OAuth and is not
claimed to be JWT. Missing, malformed, expired, incorrectly signed, and
insufficient-scope tokens receive the same generic 401 response so authentication
details are not exposed. Mutation actors come from the verified subject and are
recorded in incident events.

The local/demo profile has an explicit development fallback secret. Other
profiles require configuration. A public deployment would need an external
identity provider and secret-management design.

## Process-Local Mutation Limit

Authenticated mutation requests are limited by subject. The default policy is 10
requests per 60-second fixed window and returns HTTP 429 with `Retry-After` when
exceeded. `MCT_OPERATOR_RATE_LIMIT` and
`MCT_OPERATOR_RATE_WINDOW_SECONDS` configure the policy.

Authentication is evaluated first, so failed tokens neither consume allowance
nor receive scope-specific details. Limiter state resets on process restart and
is not shared across replicas; this is a local portfolio safeguard, not an
enterprise or distributed edge-control claim.
