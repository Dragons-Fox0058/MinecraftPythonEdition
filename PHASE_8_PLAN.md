# Phase 8 — Networking (Java Edition 1.12.2, protocol 340)

## Implemented

- [x] Signed 32-bit VarInt encoding/decoding and bounded packet framing.
- [x] Protocol strings, UUIDs, and packed block positions.
- [x] Packet compression framing with zlib and size/threshold validation.
- [x] TCP connection wrapper with exact reads, framed send/receive, and compression switching.
- [x] Protocol-340 handshake encoding/decoding for status and login.
- [x] Server status JSON query and ping/pong latency verification.
- [x] Offline-mode login and login success parsing.
- [x] Online-mode RSA public-key parsing, PKCS#1 v1.5 secret/token encryption, Minecraft signed server hash, AES/CFB8 stream encryption, and authenticated session-join callback.
- [x] HTTPS Mojang session join helper; access tokens are passed at runtime and are not logged or persisted by the networking layer.
- [x] Common play payloads for chat, keep-alive, player movement/look, held slot, and block digging.
- [x] Additional protocol-340 client settings, client status, teleport confirmation, block change, chunk unload, disconnect, health, time, and player-abilities codecs with explicit packet dispatch.
- [x] Unit tests for codec boundaries, compression, handshake, status, offline login, and play payloads.
- [x] Unit tests for the additional client settings/status/teleport and common world/player state packet decoders.
- [x] Opt-in GitHub Actions workflow to test status and offline login against the genuine Mojang 1.12.2 server JAR.

## Remaining compatibility work

- [x] RSA/AES-CFB8 transport and session join flow implemented and covered with a simulated cryptographic handshake. **Not yet validated against a live online-mode server.**
- [ ] Complete the protocol-340 packet registry for both directions and all states; the implemented registry remains intentionally partial.
- [ ] Complete play packet codecs and semantics: chunk block-entity NBT decoding, entity updates, inventory/windows, plugin messages, full chat components, and complete disconnect/reason handling.
- [ ] Integrate network state changes with world, player, inventory, entity, and chunk systems.
- [ ] Implement robust reconnect, timeout, keep-alive scheduling, and graceful disconnect behavior.
- [ ] Run the real Java 1.12.2 interoperability workflow and record the result.

## Real-server test gate

The real-server workflow is manual and runs only when the repository owner has reviewed the Minecraft EULA and explicitly set the repository Actions variable `MINECRAFT_EULA_ACCEPTED=true`. It downloads the official server JAR and verifies its published SHA-1 before launching an offline-mode test server. No test result is claimed until that workflow has actually run.

## Status

The transport, offline login, and online-mode cryptographic/session-login foundations are implemented and unit-tested. Phase 8 is **not complete**: live online-mode verification and full play packet/state integration remain.
