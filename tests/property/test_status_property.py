from hypothesis import given
from hypothesis import strategies as st

from att.models.project import ProjectStatus


@given(st.sampled_from([member.value for member in ProjectStatus]))
def test_project_status_values_are_lowercase(value: str) -> None:
    assert value == value.lower()
