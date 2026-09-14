# Plan

Use the existing Python/Docker stack: Starlette/uvicorn HTTP, Pydantic validation, cryptography Fernet payload encryption, and a distinct SQLite store. Store only opaque tenant identifiers and token digests outside encrypted envelopes. Serialize workflow writes with BEGIN IMMEDIATE; append and verify an audit chain within each transaction. All access goes through one authorization service. Public MCP remains aggregate-only.

A static same-origin browser console holds bearer credentials in memory only. Security headers prohibit framing/external assets; reject cross-origin/host requests, bound body size, rate-limit failed authentication, and disable access logs. Bind the host port to 127.0.0.1; no outbound requests are needed. The operator creates expiring tenant credentials and distributes them through a separately agreed secure channel.

An authenticated matching board shares only explicitly opted-in aggregate employer signals. Keep worker identities outside this pilot. Transition consent is an employer attestation, not independently verified worker consent. Offer/start outcomes remain self-reported. No automated hiring decisions or claims of zero unemployment.
