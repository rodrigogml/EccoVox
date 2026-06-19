import pytest

from eccovox.core.concurrency import CapacityLimiter
from eccovox.core.errors import EccoVoxError, ErrorCodeEnum


def test_capacityLimiter_shouldRejectExcessWork_whenNoSlotIsAvailable() -> None:
    limiter = CapacityLimiter(max_concurrent=1, queue_size=0)

    with limiter.acquire():
        with pytest.raises(EccoVoxError) as error:
            with limiter.acquire():
                pass

    assert error.value.code == ErrorCodeEnum.CAPACITY_EXCEEDED


def test_capacityLimiter_shouldReleaseSlot_whenContextExits() -> None:
    limiter = CapacityLimiter(max_concurrent=1, queue_size=0)

    with limiter.acquire():
        pass

    with limiter.acquire():
        acquired = True

    assert acquired
