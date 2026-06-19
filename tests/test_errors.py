import pytest

from eccovox.core.errors import ERROR_MAPPINGS, ErrorCodeEnum


@pytest.mark.parametrize(
    ("code", "http_status", "exit_code"),
    [
        (ErrorCodeEnum.INVALID_AUDIO, 400, 2),
        (ErrorCodeEnum.INVALID_TEXT, 400, 2),
        (ErrorCodeEnum.CAPABILITY_DISABLED, 404, 3),
        (ErrorCodeEnum.TIMEOUT, 408, 4),
        (ErrorCodeEnum.EMPTY_TRANSCRIPTION, 422, 5),
        (ErrorCodeEnum.UNSUPPORTED_AUDIO_FORMAT, 415, 5),
        (ErrorCodeEnum.CAPACITY_EXCEEDED, 409, 6),
        (ErrorCodeEnum.INTERNAL_ERROR, 500, 10),
    ],
)
def test_errorMappings_shouldExposeStableHttpAndCliCodes(
    code: ErrorCodeEnum,
    http_status: int,
    exit_code: int,
) -> None:
    mapping = ERROR_MAPPINGS[code]

    assert mapping.http_status == http_status
    assert mapping.cli_exit_code == exit_code
