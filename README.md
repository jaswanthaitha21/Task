
Hi Jaswanth,

Happy to answer your follow-up questions. Here are responses to each:

1. Should clients call close() and wait for cleanup before retrying — could stale connections count against limits?
Yes — always call close() and wait for the close handshake to complete before reconnecting. Abnormal closes (e.g. dropping the connection without a proper close frame) can leave stale server-side state for a few seconds, during which that slot may still count against your concurrency limit. This is likely contributing to the unexpected rate-limit errors at ~40 connections.

2. Are there limits beyond concurrent connection count?
The primary limit is concurrent WebSocket connections. Rapid reconnect attempts can also trigger rate limiting — a minimum 1–2 second delay between reconnects is recommended. There are no separately enforced limits on flush frequency or transcribe call rate within an open connection.

3. Recommended operating range for Pro plan (100 concurrent limit)?
We recommend staying at 70–80% of your plan limit under normal conditions to leave headroom for reconnects and cleanup. For a 100-connection limit, target ≤75–80 active connections at any moment.

4. How long can a closed connection remain counted against limits?
A proper close handshake releases the slot immediately. Abnormal closes (dropped without close frame) may hold the slot for a few seconds on the server side — typically 3–10 seconds, though this is not a guaranteed SLA. This is why explicit close() is important.

5. Is audio duration billed if transcribe() was accepted but the client timed out waiting for recv()?
Billing is based on audio submitted for transcription, not on whether the client received the response. If the audio was accepted server-side, the duration is counted for billing regardless of client timeout behavior.

6. If the client receives close 1003 "Rate limit exceeded", is that attempt billed?
If the connection was rate-limited at the WebSocket connection level (rejected handshake or rejected before audio processing), that audio is not billed. If audio was already being processed and then the connection was closed, the processed portion may be billed.

7. Should clients retry the same audio chunk after a 1003, or skip?
Retry with exponential backoff. The 1003 indicates a rate-limit event, not a data problem — the audio chunk is still valid. Back off, reconnect, and resend the chunk.

8. Recommended cooldown/backoff for 1003?
Exponential backoff starting at 1–2 seconds is appropriate. A minimum of 2 seconds is recommended before the first retry attempt.

9. Are malformed/invalid audio payloads counted toward usage or rate-limit counters?
Invalid audio that is rejected before processing (e.g. bad header, no audio frames) is not billed. It may count toward connection/request counters in edge cases, but valid close/reconnect flows are not penalized for one-off bad payloads.

10. Should clients retry or skip malformed audio?
Treat malformed audio as a client-side validation error. Fix or skip the payload — do not retry the same invalid data. Re-building the connection is recommended if the WebSocket was closed due to the error.

11. Is transcribe → flush → recv every 5 seconds an acceptable production pattern?
Yes. This is a supported and valid pattern for periodic low-latency analytics use cases.

12. Is waiting for recv() every 5 seconds fully supported for continuous streaming?
Yes, waiting for recv() after each 5-second flush is fully supported. It will not negatively impact throughput at that frequency. For truly continuous high-volume streaming, you can pipeline multiple flushes and collect responses asynchronously, but 5-second batches are fine.

13. Is 5-second WAV chunking a recommended chunk size?
5 seconds is a reasonable chunk size for low-latency STT. Smaller chunks (500ms–1s) reduce latency further but may reduce accuracy on incomplete utterances. Larger chunks (10–30s) improve accuracy for longer phrases but increase latency. 5s is a good balance for live analytics.

14–15. Stereo WAV support?
Mono audio (single channel) is recommended. For stereo input, the service will process the audio but behavior varies — we recommend downmixing to mono before sending for most use cases. If you have separate speakers on separate channels, downmix or send each channel separately for best results. Stereo-native diarization is not officially documented.

16. Account-side metrics (active connections, rejected handshakes, close code counts, billed seconds)?
Granular per-account telemetry of this type is not available via self-serve at this time. For usage breakdowns, the dashboard at dashboard.sarvam.ai shows credit consumption. For detailed diagnostics, please share the time window + approximate usage in your reply and the team can look into it internally.

Hope this helps you finalize your production STT WebSocket strategy. Let us know if anything is still unclear.

Best regards,
Team Sarvam

