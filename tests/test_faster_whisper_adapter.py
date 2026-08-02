import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from eccovox.core.models import CapabilityEnum, RuntimeProfile, SttRequest
from eccovox.engine.faster_whisper import FasterWhisperSttEngineAdapter


def test_transcribe_shouldReuseModelAndPreserveDetectedContainer(monkeypatch, tmp_path: Path) -> None:
    created_models = []
    received_paths = []

    class FakeWhisperModel:
        def __init__(self, model_name: str, device: str, compute_type: str) -> None:
            created_models.append((model_name, device, compute_type))

        def transcribe(self, path: str, language: str | None, initial_prompt: str | None):
            received_path = Path(path)
            received_paths.append(received_path.suffix)
            assert received_path.read_bytes().startswith(b"OggS")
            assert language == "pt"
            assert initial_prompt == "Transcrição fiel.\nContext vocabulary: Todoist, backup."
            segments = [SimpleNamespace(text=" Todoist ", start=0.0, end=1.0, avg_logprob=-0.1)]
            info = SimpleNamespace(language="pt", language_probability=0.99, duration=1.0)
            return segments, info

    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=FakeWhisperModel))
    adapter = FasterWhisperSttEngineAdapter(tmp_path)
    profile = RuntimeProfile(
        name="diagnostic",
        capability=CapabilityEnum.STT,
        engine="faster-whisper",
        model="medium",
        device="cpu",
        compute_type="int8",
    )
    request = SttRequest(
        audio=b"OggS" + b"\x00" * 32,
        audio_format="wav",
        language="pt-BR",
        prompt="Transcrição fiel.",
        context_terms=("Todoist", "backup", "todoist"),
    )

    first_result = adapter.transcribe(request, profile)
    second_result = adapter.transcribe(request, profile)

    assert created_models == [("medium", "cpu", "int8")]
    assert received_paths == [".ogg", ".ogg"]
    assert first_result.text == second_result.text == "Todoist"
    assert first_result.confidence == pytest.approx(0.904837, abs=0.000001)
    assert first_result.metadata["languageProbability"] == 0.99
    assert first_result.metadata["contextTermCount"] == 3
    assert not list(tmp_path.iterdir())
