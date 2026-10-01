# Publishing Contract (Studio + Backend Worker)

Updated: 2026-10-01. Studio creates and displays creator intent. Backend owns account-bound OAuth credentials, schedule truth, private approved assets, worker execution, provider receipts, and reconciliation.

A creator must approve cloud upload of a finished local render. Studio may create a draft for a target account and UTC time, but must display it as pending until Backend verifies provider publication. Do not treat an HTTP upload response, queued job, or accepted draft as proof of a public post. Backend capabilities must reflect live configured adapters and account connection state.

YouTube publication still requires Google credentials, an owner-bound connection, audit approval for public visibility, and a live end-to-end test. Instagram and TikTok adapters are not yet implemented. Contract changes must update Backend, Studio, and the canonical Core OpenAPI artifact together.
