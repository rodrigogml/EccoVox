from eccovox.util.audio_format import audio_format_hint, audio_suffix, detect_audio_format


def test_detectAudioFormat_shouldPreferOggMagic_whenTelegramUploadIsOpus() -> None:
    audio = b"OggS" + b"\x00" * 32

    assert detect_audio_format(audio, "wav") == "ogg"
    assert audio_suffix(audio, "wav") == ".ogg"


def test_detectAudioFormat_shouldRecognizeCommonContainers() -> None:
    assert detect_audio_format(b"RIFF\x00\x00\x00\x00WAVE") == "wav"
    assert detect_audio_format(b"fLaC\x00\x00") == "flac"
    assert detect_audio_format(b"\x1aE\xdf\xa3\x00") == "webm"
    assert detect_audio_format(b"\x00\x00\x00\x18ftypM4A ") == "m4a"


def test_audioFormatHint_shouldUseFilenameBeforeContentType() -> None:
    assert audio_format_hint("voice.ogg", "audio/wav") == "ogg"
    assert audio_format_hint(None, "audio/mpeg; charset=binary") == "mp3"


def test_audioSuffix_shouldUseBin_whenFormatIsUnknown() -> None:
    assert audio_suffix(b"not-a-known-container") == ".bin"
