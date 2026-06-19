from eccovox.api.app import create_app
from eccovox.core.models import RuntimeConfiguration, SttConfig, TtsConfig
from eccovox.core.runtime import SpeechRuntime
from eccovox.engine.base import FakeSttEngineAdapter, FakeTtsEngineAdapter


def _client():
    from fastapi.testclient import TestClient

    runtime = SpeechRuntime(
        RuntimeConfiguration(stt=SttConfig(engine="fake-stt"), tts=TtsConfig(engine="fake-tts")),
        FakeSttEngineAdapter(),
        FakeTtsEngineAdapter(),
    )
    return TestClient(create_app(runtime))


def test_health_shouldReturnCamelCaseContract() -> None:
    response = _client().get("/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["capabilities"]["stt"]["status"] == "ready"


def test_transcribe_shouldReturnJson_whenMultipartIsValid() -> None:
    response = _client().post(
        "/v1/audio/transcriptions",
        files={"file": ("input.wav", b"audio", "audio/wav")},
        data={"language": "pt-BR", "responseFormat": "json"},
    )

    assert response.status_code == 200
    assert response.json()["text"] == "texto transcrito"


def test_speech_shouldReturnAudio_whenJsonIsValid() -> None:
    response = _client().post("/v1/audio/speech", json={"input": "hello", "responseFormat": "mp3"})

    assert response.status_code == 200
    assert response.content == b"FAKEAUDIO"
    assert response.headers["content-type"] == "audio/mp3"


def test_speech_shouldReturnTopLevelError_whenTextIsInvalid() -> None:
    response = _client().post("/v1/audio/speech", json={"input": " "})

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_text"
