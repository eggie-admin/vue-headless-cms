# Samsung dev AI/RSS contract

This directory does not duplicate the KAI AI runtime.

During device development it references the canonical ordinary-Termux subsystem in
`eggie-admin/hydra-shell-android` at `ultima/ollama-ffmpeg-antenna-v3/ai_feed`.

The final APK lane remains a separate release concern. A production Secure Folder APK
must not silently acquire an undocumented dependency on an external Termux process.

No build is triggered by this staged overlay.
