# Licenses

EccoVox is intended to be free for use and is licensed as Apache-2.0 unless changed by an explicit future governance decision.

Third-party libraries, model files, voice assets and optional runtime dependencies keep their own licenses. Users and distributors must verify those licenses for their intended use, especially before redistribution, commercial packaging or production deployment.

Initial dependency notes:

| Component | Purpose | License responsibility |
|-----------|---------|------------------------|
| `faster-whisper` | STT engine adapter | Verify library, model and CTranslate2-related license terms before deployment. |
| Kokoro | TTS engine adapter | Verify package, model and voice asset license terms before deployment. |
| FastAPI/Uvicorn/Typer | HTTP and CLI runtime | Verify package license terms during dependency locking. |
| `httpx2` | Development/test dependency for FastAPI/Starlette TestClient | Verify package license terms during dependency locking. |

This document is not a legal opinion. It is an operational checklist marker for dependency review.

## Current Development Dependency Snapshot

Validated in this workspace with:

| Package | Version |
|---------|---------|
| FastAPI | 0.137.2 |
| Uvicorn | 0.49.0 |
| Typer | 0.26.7 |
| python-multipart | 0.0.32 |
| pytest | 9.1.0 |
| httpx2 | 2.4.0 |
| Starlette | 1.3.1 |
| Pydantic | 2.13.4 |

`pip show` returned empty `License` fields for these installed wheels in the local environment. A redistribution-ready release must verify package classifiers, license files and model/voice asset terms from the exact locked artifacts.
