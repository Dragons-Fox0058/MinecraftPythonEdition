# Phase 8 — Networking (Java Edition 1.12.2, protocol 340)

## Implemented

- [x] Signed 32-bit VarInt encoding/decoding and bounded packet framing.
- [x] Protocol strings, UUIDs, and packed block positions.
- [x] Packet compression framing with zlib and size/threshold validation.
- [x] TCP connection wrapper with exact reads, framed send/receive, and compression switching.
- [x] Protocol-340 handshake encoding/decoding for status and login.
- [x] Server status JSON query and ping/pong latency verification.
- [x] Offline-mode login, login success parsing, compression negotiation, and explicit rejection of online-mode encryption requests.
- [x] Common play payloads for chat, keep-alive, player movement/look, held slot, and block digging.
- [x] Unit tests for codec boundaries, compression, handshake, status, offline login, and play payloads.
- [x] Opt-in GitHub Actions workflow to test status and offline login against the genuine Mojang 1.12.2 server JAR.

## Remaining compatibility work

- [ ] Implement RSA server-key handling, AES/CFB8 stream encryption, and supported Microsoft/Mojang session authentication for online-mode servers.
- [ ] Complete the protocol-340 packet registry for both directions and all states.
- [ ] Implement complete play packet codecs: chunk data, block changes, entity updates, inventory/windows, player abilities, plugin messages, chat components, and disconnect handling.
- [ ] Integrate network state changes with world, player, inventory, entity, and chunk systems.
- [ ] Implement robust reconnect, timeout, keep-alive scheduling, and graceful disconnect behavior.
- [ ] Run the real Java 1.12.2 interoperability workflow and record the result.

## Real-server test gate

The real-server workflow is manual and runs only when the repository owner has reviewed the Minecraft EULA and explicitly set the repository Actions variable `MINECRAFT_EULA_ACCEPTED=true`. It downloads the official server JAR and verifies its published SHA-1 before launching an offline-mode test server. No test result is claimed until that workflow has actually run.

## Status

The transport and offline login foundations are implemented. Phase 8 is **not complete**: online-mode encryption/authentication and the full play packet/state integration remain.
