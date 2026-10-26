import pytest
from pydantic import ValidationError

from app.config import Settings


@pytest.mark.parametrize("value", [0, -1])
def test_max_llm_attempts_must_be_positive(value):
    with pytest.raises(ValidationError):
        Settings(max_llm_attempts=value)
