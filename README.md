Hi Sarvam team,

Thanks for the earlier clarification. We have a few final STT WebSocket questions so we can tune our client behavior correctly for production use.

The most important question for us is #1 below, as we suspect it may explain the rate-limit behavior we are observing.

1. We estimate our workload should stay below ~40 parallel STT WebSocket connections, yet we occasionally receive 1003 "Rate limit exceeded" responses.
   
   In some failure scenarios (e.g., send/recv timeout, broken connection, or 1003 response), our current implementation immediately creates a new WebSocket and retries without explicitly calling "close()" on the previous socket, since we assume the connection is already unusable.
   
   Should clients explicitly call "close()" and wait for cleanup before retrying/reconnecting, even when the connection appears dead? Could failing to do so cause stale connections to remain counted against concurrency limits and contribute to unexpected rate-limit errors?
   
   Additionally, are there any limits beyond concurrent WebSocket count (e.g., connection creation rate, reconnect rate, flush frequency, or request rate) that we should be aware of?

2. For the Pro plan's 100 concurrent STT WebSocket limit, what operating range would you recommend in production to account for reconnects and cleanup delays?

3. After an abnormal close or timeout, can a connection remain counted against concurrency limits for some period server-side? If so, approximately how long?

4. For STT WebSocket, if "transcribe(audio)" is accepted server-side but the client fails or times out while waiting for "recv()", is that audio duration counted for billing/usage?

5. If a client sends audio and then receives websocket close code 1003 with reason "Rate limit exceeded", is that attempt counted for billing/usage, or are only successful transcription responses billed?

6. For 1003 + "Rate limit exceeded", should the client retry the same audio chunk after a cooldown, or skip that chunk and continue with later audio?

7. If retrying the same chunk is recommended, what cooldown/backoff strategy do you suggest? Is exponential backoff acceptable, and what minimum cooldown would you recommend?

8. For low-latency live STT where audio arrives every 5 seconds and transcripts are needed every 5 seconds, is a "transcribe -> flush -> recv" cycle per chunk an acceptable production pattern?

9. You mentioned continuous streaming can send chunks and flush periodically without waiting for "recv()" after every flush. For a live analytics use case, is waiting for "recv()" every 5 seconds fully supported, or could it negatively impact throughput/latency?

10. Is 5-second WAV chunking a recommended chunk size for low-latency STT, or do you suggest smaller/larger chunks?

11. For stereo WAV input, is stereo officially supported? If stereo audio is sent, does the service process both channels, downmix to mono, or use only one channel?

12. If separate speakers are present on separate stereo channels, do you recommend sending stereo as-is or downmixing to mono before STT?

13. Can support provide account-side metrics for a specific time window, such as active STT WebSocket count, rejected handshakes, close-code counts, and billed STT seconds/minutes?

These answers will help us understand the observed rate-limit behavior, avoid retry storms, and implement a production-safe STT WebSocket strategy.

Thank you.
