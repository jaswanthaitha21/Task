Hi Jaswanth,

Thanks for the detailed write-up. Here are answers to each question:

1. Is {"type":"ping"} supported for STT WebSockets?
Not officially documented. The recommended approach is to keep sending audio. For idle periods, close and reconnect when a new call starts rather than holding a silent connection open.

2. Is transcribe to flush to recv the right pattern?
Yes. For continuous live streaming you can keep sending chunks and flush periodically without waiting for recv after every flush.

3. Should 1003 + "Rate limit exceeded" be treated as a rate-limit event?
Yes - the reason string is the definitive signal. Treat it as a rate-limit event and back off before reconnecting.

4. Reconnect strategy?
Exponential backoff - start with 1-2 seconds and increase on repeated failures. Immediate reconnect will typically hit the same error again.

5. Are reconnect handshakes/flush/transcribe rate-limited separately?
The Pro plan limit is 100 concurrent WebSocket connections. Rapid reconnect attempts can also trigger rate limiting - a minimum 1-2 second delay between reconnects is recommended. Flush/transcribe within an open connection are not separately rate-limited.

6. How long does a closed connection count toward the concurrent limit?
Released when the close handshake completes. Abnormal closes may take a few seconds to clear server-side. Explicit close() calls are recommended over dropping connections.

7. Recommended audio chunk duration?
5-second WAV at 8 kHz is fine. Smaller chunks (500ms-1s) reduce latency. No hard maximum, but very large chunks increase processing time.

8. Limits on flush()/recv() frequency?
No explicit per-connection limits. However, very frequent flushing after tiny chunks can reduce transcription accuracy - the model benefits from hearing longer utterances.

Docs: STT WebSocket Overview

If you continue hitting rate limits frequently, a Business plan upgrade provides higher concurrent connection limits. Let us know if you need more details.

Best regards,
Team Sarvam
