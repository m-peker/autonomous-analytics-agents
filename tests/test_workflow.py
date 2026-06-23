"""Tests for the pipeline state and workflow."""
from __future__ import annotations

from src.workflow.state import PipelineState


class TestPipelineState:
    def test_default_state(self):
        state = PipelineState()
        assert state.file_paths == []
        assert state.urls == []
        assert state.user_query == ""
        assert state.confidence_score == 0
        assert state.errors == []

    def test_state_with_inputs(self):
        state = PipelineState(
            file_paths=["data/test.xlsx"],
            urls=["https://example.com"],
            user_query="Analyze sales",
            model="gpt-4o-mini",
        )
        assert len(state.file_paths) == 1
        assert len(state.urls) == 1
        assert state.model == "gpt-4o-mini"
