import asyncio

import httpx

from eccovox.api.app import create_app
from eccovox.core.models import RuntimeConfiguration, SttConfig, TtsConfig
from eccovox.core.runtime import SpeechRuntime
from eccovox.engine.base import FakeSttEngineAdapter, FakeTtsEngineAdapter


def _app():
    runtime = SpeechRuntime(
        RuntimeConfiguration(stt=SttConfig(engine="fake-stt"), tts=TtsConfig(engine="fake-tts")),
        FakeSttEngineAdapter(),
        FakeTtsEngineAdapter(),
    )
    return create_app(runtime)


async def _request(method: str, path: str, **kwargs):
    transport = httpx.ASGITransport(app=_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await getattr(client, method)(path, **kwargs)


def _call(method: str, path: str, **kwargs):
    return asyncio.run(_request(method, path, **kwargs))


def test_health_shouldReturnCamelCaseContract() -> None:
    response = _call("get", "/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["capabilities"]["stt"]["status"] == "ready"


def test_transcribe_shouldReturnJson_whenMultipartIsValid() -> None:
    response = _call(
        "post",
        "/v1/audio/transcriptions",
        files={"file": ("input.wav", b"audio", "audio/wav")},
        data={"language": "pt-BR", "responseFormat": "json"},
    )

    assert response.status_code == 200
    assert response.json()["text"] == "texto transcrito"


def test_speech_shouldReturnAudio_whenJsonIsValid() -> None:
    response = _call("post", "/v1/audio/speech", json={"input": "hello", "responseFormat": "mp3"})

    assert response.status_code == 200
    assert response.content == b"FAKEAUDIO"
    assert response.headers["content-type"] == "audio/mp3"


def test_speech_shouldReturnTopLevelError_whenTextIsInvalid() -> None:
    response = _call("post", "/v1/audio/speech", json={"input": " "})

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_text"
