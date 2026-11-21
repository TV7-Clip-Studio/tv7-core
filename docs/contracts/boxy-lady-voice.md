# Boxy Lady voice consumer boundary

TV7 owns the character/script, video timing, presenter staging and final mix. Boxy Lady owns voice references, generation/conversion, immutable takes and audio delivery. Consumers pin identity/version and review exact returned audio before adoption. Other game/video consumers use the same boundary; provider internals do not belong in TV7.

## Current connections

Private operator configuration launches two local stdio MCP processes for the TV7 pilot: synthesis in the MLX environment, conversion in the isolated RVC environment. They share a TV7-scoped private workspace and the existing inference lock. Tool discovery advertises the same names on each server; callers must select the appropriate worker. A unified provider-selecting worker is a Boxy Lady follow-up. Registration in the Codex configuration does not mean a running chat has hot-loaded the new tools.

`tooling/boxy_voice_client.py --config /private/connection.json` reads a trusted local command array, performs MCP initialization, discovery and identity listing, then closes the session. It does not submit inference. The Python client supports explicit tool calls within one live session. Request IDs and response limits are checked; tool errors, timeouts and process failure propagate without retry. The owner reconciles jobs/takes before an intentional new attempt. On shutdown the owned server gets EOF for cancellation cleanup; a nonresponsive owned process group is terminated after the grace period.

Connection JSON contains `command`: an argument array launching the provider with root, registry, worker interpreter and MCP mode. No operator paths, references or credentials belong in public configuration. Use an explicit workspace per consumer. Current process-local job IDs are valid in their originating live server session; a shared inference lock does not make job history durable.

## Versioned handoff

The Boxy Lady owner implements `boxy-lady.audition-request.v1` and `boxy-lady.audition-delivery.v1`. TV7 prepares immutable passage text/hashes and creative direction, submits once under a named owner, then verifies the frozen request, item outcomes and audio artifacts. The exact provider schema lives in Boxy Lady rather than a second competing implementation here. Delivery verification must distinguish partial, technically valid and listening-accepted outputs. A completed audition is not voice promotion.

The first pilot is capped at three passages (short/reaction/long), native candidate plus matched Quicksilver and prior-conversion controls. Dry acceptance precedes metallic or musical variants. Reference leads without a suitable recording/transcript or a validated explicit conditioning mode remain visibly unresolved. Caption text is the canonical submitted text; RMS envelopes are not word alignment.

## Validation

Run `PYTHONPATH=tooling python3 -m unittest discover -s tooling/tests -p test_boxy_voice_client.py` or `make check`. Unit tests use a fake subprocess for protocol errors, timeouts and no-retry behavior. Live discovery/status checks are separate private evidence. Connection tests do not establish naturalness, native Patois pronunciation or artistic acceptance.

`tooling/boxy_voice_delivery.py --directory /private/delivery --request-sha256 HASH --delivery-sha256 HASH` independently checks the trusted request/delivery checksums, artifact inventory, canonical text, PCM metadata and identity versions. Expected checksums come from the owning agent's handoff, not just the adjacent checksum file. It reports partial outcomes and leaves listening/promotion unset. The provider's full schema and source-qualification checks remain in Boxy Lady.

## Performance direction and selection

The provider can preserve a versioned performance brief and report which controls are applied versus documentary intent. An authored phrase plan can preserve exact canonical text and insert explicit pauses between generated phrase masters. It does not establish word alignment or guarantee stress, intonation or emotional delivery. Preserve raw phrase audio and inspect the provider support receipt before treating a direction as executable. These capabilities live in Boxy Lady; TV7 does not duplicate its provider implementation.

Human selection belongs in a separate private record bound to reference, identity and audition hashes. Approval of a voice direction does not approve failed takes or every comparison lane. Preserve the previous identity for rollback and keep generated-take listening acceptance distinct from direction selection. Artist references, consumer character mappings and recordings stay outside this public repository.
