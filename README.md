Inspect my repository (frontend HTML/JS and backend FastAPI Python code) to fix an OOMKilled issue when users upload 1.5GB–2GB advertisement and YouTube videos for Gemini social media compliance checks.

### Hard Constraints:
- I CANNOT edit Kubernetes YAML files, pod resources (strict 500m CPU / 500Mi RAM), or cluster infrastructure.
- Everything must be solved purely within the application codebase (HTML/JS frontend and FastAPI Python backend).
- Compressed videos MUST preserve **720p resolution** (`scale=-2:720`), **2 FPS** (`-r 2` to catch fast ad cuts and brief on-screen disclaimers), and **clear mono audio** (`-ac 1 -c:a aac -b:a 64k` so Gemini can audit spoken claims and voiceovers).
- Users may upload multiple videos sequentially in one session OR upload simultaneously from multiple browsers/tabs.
- Compression must be **fast** (must not stall the user or cause timeouts).
- After Gemini returns a response, temporary files must be deleted AND pod memory (RSS) must actively drop back down.

### Task:
1. Audit my current frontend upload flow and FastAPI backend to identify where large uploads are buffered into RAM or causing concurrency spikes.
2. Implement a **Hybrid Client + Server Architecture** across my frontend and backend files:

   **A. Frontend (Fast Client-Side Compression + Sequential Upload Queue):**
   - Use `@ffmpeg/ffmpeg` (`ffmpeg.wasm`) in the browser to compress videos before uploading so the 500Mi pod never receives raw 2GB files.
   - Use these exact `ffmpeg` flags for **720p + 2 FPS + Audio + Maximum Speed**:
     `-vf scale=-2:720 -r 2 -c:v libx264 -preset ultrafast -tune zerolatency -crf 28 -ac 1 -c:a aac -b:a 64k`
     (Keeps crisp 720p text/disclaimers, captures 2 frames/sec for fast ad cuts, keeps voiceovers intact, compresses ~10x faster than standard presets, and shrinks 2GB to ~30–55MB).
   - Display real-time compression & upload progress in the UI.
   - If a user uploads multiple videos one-by-one or in a batch, process and upload them through a **sequential client queue** (one after another) instead of running parallel compressions in the same tab.
   - Immediately delete `ffmpeg.wasm` virtual files (`ffmpeg.deleteFile(...)`) and clear JS Blob/ArrayBuffer references after each upload so browser memory stays low across multiple uploads.

   **B. Backend FastAPI (Multi-Browser Concurrency Protection + Gemini 2 FPS Sampling + Explicit RAM Release):**
   - At app startup (before FastAPI routes initialize), set `tempfile.tempdir` to a disk-backed folder inside the app working directory (e.g., `./tmp_uploads`) instead of RAM-backed `/tmp`.
   - Stream incoming request uploads to disk in `1MB` chunks (never call `await file.read()`).
   - **Multi-Browser Concurrency Guard:** Use a `threading.Semaphore(1)` around the processing/Gemini upload step so simultaneous uploads from multiple browsers queue cleanly one-by-one instead of OOMKilling the 500Mi pod.
   - If a file still requires server-side compression (e.g., fallback), use `-vf scale=-2:720 -r 2 -c:v libx264 -preset ultrafast -crf 28 -threads 1 -ac 1 -c:a aac -b:a 64k`.
   - When calling Gemini with the uploaded video file, pass `video_metadata=types.VideoMetadata(fps=2)` (if using `google-genai` SDK) so Gemini analyzes both frames per second rather than defaulting back to 1 FPS.
   - **Strict Cleanup & Memory Release (`finally:` block):**
     - Delete local temporary files from disk (`os.remove`).
     - Delete the uploaded file from Gemini File API (`client.files.delete(...)`).
     - Run `gc.collect()` AND call `ctypes.CDLL("libc.so.6").malloc_trim(0)` (wrapped in try/except for Linux) so Python/glibc returns freed heap memory back to the Kubernetes container OS immediately after every request.

3. Provide the exact updated code for my frontend and backend files while preserving my existing UI design and compliance report output format.
4. 
