# Bug: `gql<4.0.0` cap transitively pins `websockets<12`, making specklepy uninstallable alongside modern websockets consumers

## Prerequisites

- [x] I read the contribution guidelines
- [x] I checked the documentation and found no answer.
- [x] I checked existing issues and found no similar issue.
- [x] I checked the community forum for related discussions and found no answer.
- [x] I'm reporting the issue to the correct repository.

## What package are you referring to?

`specklepy` (packaging / dependency metadata).

## Describe the bug

Since **3.0.9**, specklepy declares:

```toml
"gql[requests,websockets]>=3.5.0,<4.0.0"
```

The `<4.0.0` cap was added in #456 (commit `c9a0e45`, merged 2025-10-01), titled *"limit gql package version to not upgrade to latest major version"*.

The problem is what that cap implies transitively. `gql`'s `websockets` extra is a hard, narrow range:

| gql | `websockets` extra requires |
|---|---|
| 3.5.3 (newest 3.x) | `websockets>=10,<12` |
| 4.0.0 (current latest) | `websockets>=14.2,<16` |

Because specklepy requests the `websockets` extra unconditionally, **capping gql at `<4` pins `websockets<12` for the entire environment**. websockets 12 was released in 2023; the current series is 15/16. So specklepy can no longer be co-installed with any package that requires `websockets>=12`.

Concretely, specklepy and [marimo](https://github.com/marimo-team/marimo) (which requires `websockets>=14.2.0` since 0.23.9) are now mutually exclusive:

```
Because gql[websockets]>=3.5.0,<=3.6.0b4 depends on websockets>=10,<12
and marimo>=0.23.9 depends on websockets>=14.2.0, we can conclude that
marimo>=0.23.9 and gql[websockets]>=3.5.0,<=3.6.0b4 are incompatible.
And because specklepy>=2026.6.0 depends on gql[websockets]>=3.5.0,<4.0.0,
we can conclude that marimo>=0.23.9 and specklepy>=2026.6.0 are incompatible.
```

The only specklepy release that resolves against a current marimo is **3.0.8**, the last one before the cap — a resolver backtracking to it is the only reason installs still succeed, which is a silent ~1-year downgrade.

## To Reproduce

```toml
# pyproject.toml (or PEP 723 inline script metadata)
requires-python = ">=3.12"
dependencies = [
    "marimo>=0.23.9",
    "specklepy==2026.6.0",
]
```

`uv sync` (or `pip install`) fails with the resolution error above. Same result for every specklepy from 3.0.9 to 2026.6.0.

## Expected behavior

specklepy should not force a 2023-era `websockets` on downstream environments. Installing it next to any current websockets consumer should resolve.

## Additional context — was the cap load-bearing?

It reads as precautionary rather than a response to a known break: gql 4.0.0 was released 2025-08-17, the cap landed 2025-10-01, PR #456's description is the unfilled template with no linked issue, and it changed only the version range (no code changes). If there *was* a concrete gql 4 incompatibility, it would be very helpful to record it — it isn't captured anywhere I could find.

specklepy's gql API surface is small and stable across the 3→4 major:

- `from gql import Client, gql`
- `RequestsHTTPTransport(url=, verify=, retries=, timeout=)` — `core/api/client.py`
- `WebsocketsTransport(url=, init_payload=)` — `core/api/client.py`
- `TransportServerError`, `TransportQueryError`

All of these exist unchanged in gql 4.0.0.

I tested **specklepy 2026.6.0 against gql 4.0.0 + websockets 15.0.1** (forced via a uv dependency override), driving it against a local stub GraphQL server so no real deployment or credential was involved:

```
specklepy  2026.6.0
gql        4.0.0
websockets 15.0.1

1. transport kwargs accepted : RequestsHTTPTransport + WebsocketsTransport
2. SpeckleClient constructed : Client
3. authenticate_with_token   : http=RequestsHTTPTransport ws=WebsocketsTransport
4. Client.execute()          : {'data': None}

ALL OK on gql 4.0.0
```

That covers client construction, the `authenticate_with_token` path (which rebuilds both transports and issues real `activeUser` + `serverInfo` queries), and the `Client.execute` round trip every resource goes through.

**Caveat:** this is a stub server, not a real Speckle deployment, and I did not run specklepy's own test suite — so treat it as evidence the API surface is compatible, not as a full compatibility guarantee. CI against gql 4 would settle it properly.

## Proposed Solution

1. **Relax the cap** to `gql[requests,websockets]>=3.5.0,<5.0.0` (or require `>=4.0.0` outright, which also gets you a maintained websockets range). If the intent is only to avoid silently absorbing a *future* major, `<5.0.0` achieves that without excluding the current one.

2. **Optionally, make websockets an extra.** Only GraphQL subscriptions need it, but `gql[requests,websockets]` constrains every user's environment regardless. Moving it behind something like `specklepy[subscriptions]` would leave non-subscription users (likely the majority) entirely unconstrained, and would make this class of conflict impossible.

If a pin against a specific gql major is genuinely needed, pinning the *transitive* dependency directly (`websockets>=10,<12` in specklepy's own metadata) would at least make the real constraint visible to users hitting the resolver error.

### Workaround for anyone else hitting this

With uv, override the transitive constraint:

```toml
[tool.uv]
override-dependencies = ["websockets>=14.2.0"]
```

Note this does not survive `uv export`, so tools that flatten to a `requirements.txt` (e.g. marimo's `--sandbox` mode) will still fail.

## System Info

- specklepy 2026.6.0 (also reproduced on 3.0.9 – 3.2.8)
- Python 3.12.13
- uv 0.11.31
- Windows 11

#### Optional: Affected Projects

Any environment combining specklepy with a modern `websockets` consumer — [marimo](https://github.com/marimo-team/marimo) `>=0.23.9` is the case I hit.
