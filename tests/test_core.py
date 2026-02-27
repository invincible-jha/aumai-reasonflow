"""Comprehensive tests for aumai_reasonflow core and models.

Covers:
- ReasoningStep model validation
- ReasoningChain model and add_step behaviour
- ChainBuilder fluent API
- ChainVisualizer (Mermaid + text)
- FallacyDetector (all checks)
- ChainValidation computed properties
- Edge cases and error paths
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from aumai_reasonflow.core import ChainBuilder, ChainVisualizer, FallacyDetector
from aumai_reasonflow.models import (
    ChainValidation,
    FallacyType,
    ReasoningChain,
    ReasoningStep,
    StepType,
    ValidationIssue,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def simple_chain() -> ReasoningChain:
    """Minimal valid chain: one premise, one inference, one conclusion."""
    return (
        ChainBuilder("c1", "Simple Argument")
        .premise("p1", "All men are mortal.")
        .premise("p2", "Socrates is a man.")
        .inference("i1", "Socrates is mortal.", depends_on=["p1", "p2"])
        .conclusion("c1", "Therefore Socrates will die.", depends_on=["i1"])
        .build()
    )


@pytest.fixture()
def detector() -> FallacyDetector:
    return FallacyDetector()


@pytest.fixture()
def visualizer() -> ChainVisualizer:
    return ChainVisualizer()


# ---------------------------------------------------------------------------
# ReasoningStep model tests
# ---------------------------------------------------------------------------


class TestReasoningStep:
    def test_default_step_type_is_inference(self) -> None:
        step = ReasoningStep(step_id="s1", content="Some claim.")
        assert step.step_type == StepType.INFERENCE

    def test_whitespace_stripped_from_step_id(self) -> None:
        step = ReasoningStep(step_id="  s1  ", content="claim")
        assert step.step_id == "s1"

    def test_whitespace_stripped_from_content(self) -> None:
        step = ReasoningStep(step_id="s1", content="  stripped  ")
        assert step.content == "stripped"

    def test_confidence_default_is_1(self) -> None:
        step = ReasoningStep(step_id="s1", content="claim")
        assert step.confidence == 1.0

    def test_confidence_below_zero_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ReasoningStep(step_id="s1", content="claim", confidence=-0.1)

    def test_confidence_above_one_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ReasoningStep(step_id="s1", content="claim", confidence=1.1)

    def test_confidence_boundary_zero(self) -> None:
        step = ReasoningStep(step_id="s1", content="claim", confidence=0.0)
        assert step.confidence == 0.0

    def test_confidence_boundary_one(self) -> None:
        step = ReasoningStep(step_id="s1", content="claim", confidence=1.0)
        assert step.confidence == 1.0

    def test_empty_step_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ReasoningStep(step_id="", content="claim")

    def test_empty_content_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ReasoningStep(step_id="s1", content="")

    def test_depends_on_defaults_empty(self) -> None:
        step = ReasoningStep(step_id="s1", content="claim")
        assert step.depends_on == []

    def test_notes_defaults_to_none(self) -> None:
        step = ReasoningStep(step_id="s1", content="claim")
        assert step.notes is None

    def test_notes_can_be_set(self) -> None:
        step = ReasoningStep(step_id="s1", content="claim", notes="important")
        assert step.notes == "important"

    def test_all_step_types_accepted(self) -> None:
        for step_type in StepType:
            step = ReasoningStep(step_id="s1", content="claim", step_type=step_type)
            assert step.step_type == step_type


# ---------------------------------------------------------------------------
# ReasoningChain model tests
# ---------------------------------------------------------------------------


class TestReasoningChain:
    def test_empty_chain_has_no_steps(self) -> None:
        chain = ReasoningChain(chain_id="c1", title="Test")
        assert len(chain.steps) == 0

    def test_add_step_stores_by_id(self) -> None:
        chain = ReasoningChain(chain_id="c1", title="Test")
        step = ReasoningStep(step_id="s1", content="claim")
        chain.add_step(step)
        assert "s1" in chain.steps

    def test_add_duplicate_step_raises(self) -> None:
        chain = ReasoningChain(chain_id="c1", title="Test")
        step = ReasoningStep(step_id="s1", content="claim")
        chain.add_step(step)
        with pytest.raises(ValueError, match="already exists"):
            chain.add_step(ReasoningStep(step_id="s1", content="another claim"))

    def test_get_conclusions_filters_correctly(self) -> None:
        chain = ReasoningChain(chain_id="c1", title="Test")
        chain.add_step(ReasoningStep(step_id="p1", content="premise", step_type=StepType.PREMISE))
        chain.add_step(ReasoningStep(step_id="c1", content="conclusion", step_type=StepType.CONCLUSION))
        conclusions = chain.get_conclusions()
        assert len(conclusions) == 1
        assert conclusions[0].step_id == "c1"

    def test_get_premises_filters_correctly(self) -> None:
        chain = ReasoningChain(chain_id="c1", title="Test")
        chain.add_step(ReasoningStep(step_id="p1", content="premise", step_type=StepType.PREMISE))
        chain.add_step(ReasoningStep(step_id="i1", content="inference", step_type=StepType.INFERENCE))
        premises = chain.get_premises()
        assert len(premises) == 1
        assert premises[0].step_id == "p1"

    def test_description_defaults_none(self) -> None:
        chain = ReasoningChain(chain_id="c1", title="Test")
        assert chain.description is None

    def test_description_can_be_set(self) -> None:
        chain = ReasoningChain(chain_id="c1", title="Test", description="A test chain")
        assert chain.description == "A test chain"

    def test_multiple_steps_added(self) -> None:
        chain = ReasoningChain(chain_id="c1", title="Test")
        for i in range(5):
            chain.add_step(ReasoningStep(step_id=f"s{i}", content=f"claim {i}"))
        assert len(chain.steps) == 5


# ---------------------------------------------------------------------------
# ChainBuilder tests
# ---------------------------------------------------------------------------


class TestChainBuilder:
    def test_build_returns_reasoning_chain(self) -> None:
        chain = ChainBuilder("c1", "Test").build()
        assert isinstance(chain, ReasoningChain)

    def test_chain_id_and_title_set(self) -> None:
        chain = ChainBuilder("my_id", "My Title").build()
        assert chain.chain_id == "my_id"
        assert chain.title == "My Title"

    def test_description_passed_through(self) -> None:
        chain = ChainBuilder("c1", "T", description="desc").build()
        assert chain.description == "desc"

    def test_premise_adds_premise_step(self) -> None:
        chain = ChainBuilder("c1", "T").premise("p1", "All X are Y.").build()
        assert chain.steps["p1"].step_type == StepType.PREMISE

    def test_inference_adds_inference_step(self) -> None:
        chain = ChainBuilder("c1", "T").inference("i1", "Therefore Z.").build()
        assert chain.steps["i1"].step_type == StepType.INFERENCE

    def test_conclusion_adds_conclusion_step(self) -> None:
        chain = ChainBuilder("c1", "T").conclusion("c1", "Final.").build()
        assert chain.steps["c1"].step_type == StepType.CONCLUSION

    def test_assumption_adds_assumption_step(self) -> None:
        chain = ChainBuilder("c1", "T").assumption("a1", "Assume X.").build()
        assert chain.steps["a1"].step_type == StepType.ASSUMPTION

    def test_assumption_default_confidence(self) -> None:
        chain = ChainBuilder("c1", "T").assumption("a1", "Assume X.").build()
        assert chain.steps["a1"].confidence == 0.8

    def test_evidence_adds_evidence_step(self) -> None:
        chain = ChainBuilder("c1", "T").evidence("e1", "Data shows X.").build()
        assert chain.steps["e1"].step_type == StepType.EVIDENCE

    def test_fluent_chaining_returns_self(self) -> None:
        builder = ChainBuilder("c1", "T")
        result = builder.premise("p1", "claim")
        assert result is builder

    def test_depends_on_stored(self) -> None:
        chain = (
            ChainBuilder("c1", "T")
            .premise("p1", "A")
            .inference("i1", "B", depends_on=["p1"])
            .build()
        )
        assert chain.steps["i1"].depends_on == ["p1"]

    def test_notes_stored(self) -> None:
        chain = ChainBuilder("c1", "T").premise("p1", "A", notes="important").build()
        assert chain.steps["p1"].notes == "important"

    def test_add_step_generic(self) -> None:
        chain = (
            ChainBuilder("c1", "T")
            .add_step("r1", "Rebuttal text", StepType.REBUTTAL)
            .build()
        )
        assert chain.steps["r1"].step_type == StepType.REBUTTAL

    def test_empty_builder_yields_empty_steps(self) -> None:
        chain = ChainBuilder("c1", "T").build()
        assert len(chain.steps) == 0

    def test_full_chain_step_count(self, simple_chain: ReasoningChain) -> None:
        assert len(simple_chain.steps) == 4


# ---------------------------------------------------------------------------
# ChainVisualizer tests
# ---------------------------------------------------------------------------


class TestChainVisualizer:
    def test_mermaid_starts_with_flowchart(
        self, visualizer: ChainVisualizer, simple_chain: ReasoningChain
    ) -> None:
        result = visualizer.to_mermaid(simple_chain)
        assert result.startswith("flowchart TD")

    def test_mermaid_contains_title_comment(
        self, visualizer: ChainVisualizer, simple_chain: ReasoningChain
    ) -> None:
        result = visualizer.to_mermaid(simple_chain)
        assert "Simple Argument" in result

    def test_mermaid_contains_all_step_ids(
        self, visualizer: ChainVisualizer, simple_chain: ReasoningChain
    ) -> None:
        result = visualizer.to_mermaid(simple_chain)
        for step_id in simple_chain.steps:
            assert step_id in result

    def test_mermaid_contains_edges(
        self, visualizer: ChainVisualizer, simple_chain: ReasoningChain
    ) -> None:
        result = visualizer.to_mermaid(simple_chain)
        assert "-->" in result

    def test_mermaid_empty_chain(
        self, visualizer: ChainVisualizer
    ) -> None:
        chain = ReasoningChain(chain_id="c1", title="Empty")
        result = visualizer.to_mermaid(chain)
        assert "flowchart TD" in result

    def test_text_starts_with_chain_header(
        self, visualizer: ChainVisualizer, simple_chain: ReasoningChain
    ) -> None:
        result = visualizer.to_text(simple_chain)
        assert result.startswith("Chain: Simple Argument")

    def test_text_includes_chain_id(
        self, visualizer: ChainVisualizer, simple_chain: ReasoningChain
    ) -> None:
        result = visualizer.to_text(simple_chain)
        assert "id=c1" in result

    def test_text_includes_step_content(
        self, visualizer: ChainVisualizer, simple_chain: ReasoningChain
    ) -> None:
        result = visualizer.to_text(simple_chain)
        assert "All men are mortal." in result

    def test_text_includes_description(
        self, visualizer: ChainVisualizer
    ) -> None:
        chain = ChainBuilder("c1", "T", description="My description").premise("p1", "A").build()
        result = visualizer.to_text(chain)
        assert "My description" in result

    def test_text_includes_notes(
        self, visualizer: ChainVisualizer
    ) -> None:
        chain = ChainBuilder("c1", "T").premise("p1", "A", notes="key note").build()
        result = visualizer.to_text(chain)
        assert "key note" in result

    def test_text_confidence_shown_as_percent(
        self, visualizer: ChainVisualizer
    ) -> None:
        chain = ChainBuilder("c1", "T").premise("p1", "A", confidence=0.75).build()
        result = visualizer.to_text(chain)
        assert "75%" in result

    def test_safe_id_replaces_hyphens(self, visualizer: ChainVisualizer) -> None:
        assert visualizer._safe_id("step-one") == "step_one"

    def test_safe_id_replaces_dots(self, visualizer: ChainVisualizer) -> None:
        assert visualizer._safe_id("step.one") == "step_one"

    def test_safe_id_replaces_spaces(self, visualizer: ChainVisualizer) -> None:
        assert visualizer._safe_id("step one") == "step_one"

    def test_truncate_short_text_unchanged(self, visualizer: ChainVisualizer) -> None:
        assert visualizer._truncate("short", 40) == "short"

    def test_truncate_long_text_gets_ellipsis(self, visualizer: ChainVisualizer) -> None:
        long_text = "a" * 50
        result = visualizer._truncate(long_text, 40)
        assert len(result) == 40
        assert result.endswith("...")

    def test_depth_zero_for_no_deps(
        self, visualizer: ChainVisualizer, simple_chain: ReasoningChain
    ) -> None:
        depth = visualizer._depth("p1", simple_chain)
        assert depth == 0

    def test_depth_one_for_single_dep(
        self, visualizer: ChainVisualizer, simple_chain: ReasoningChain
    ) -> None:
        depth = visualizer._depth("i1", simple_chain)
        assert depth == 1

    def test_depth_two_for_transitive_dep(
        self, visualizer: ChainVisualizer, simple_chain: ReasoningChain
    ) -> None:
        depth = visualizer._depth("c1", simple_chain)
        assert depth == 2

    def test_topological_sort_premises_before_conclusions(
        self, visualizer: ChainVisualizer, simple_chain: ReasoningChain
    ) -> None:
        ordered = visualizer._topological_sort(simple_chain)
        ids = [s.step_id for s in ordered]
        assert ids.index("p1") < ids.index("c1")
        assert ids.index("i1") < ids.index("c1")

    def test_mermaid_shapes_all_types_covered(self, visualizer: ChainVisualizer) -> None:
        for step_type in StepType:
            assert step_type in visualizer._MERMAID_SHAPES


# ---------------------------------------------------------------------------
# FallacyDetector tests
# ---------------------------------------------------------------------------


class TestFallacyDetector:
    def test_valid_chain_is_valid(
        self, detector: FallacyDetector, simple_chain: ReasoningChain
    ) -> None:
        result = detector.validate(simple_chain)
        assert result.is_valid is True
        assert result.errors == []

    def test_valid_chain_step_count(
        self, detector: FallacyDetector, simple_chain: ReasoningChain
    ) -> None:
        result = detector.validate(simple_chain)
        assert result.step_count == 4

    def test_broken_dependency_detected(self, detector: FallacyDetector) -> None:
        chain = (
            ChainBuilder("c1", "T")
            .inference("i1", "B", depends_on=["nonexistent"])
            .build()
        )
        result = detector.validate(chain)
        assert result.is_valid is False
        broken = [i for i in result.issues if i.fallacy_type == FallacyType.BROKEN_DEPENDENCY]
        assert len(broken) == 1

    def test_unsupported_conclusion_detected(self, detector: FallacyDetector) -> None:
        chain = ChainBuilder("c1", "T").conclusion("c1", "Final.").build()
        result = detector.validate(chain)
        assert result.is_valid is False
        unsupported = [
            i for i in result.issues if i.fallacy_type == FallacyType.UNSUPPORTED_CONCLUSION
        ]
        assert len(unsupported) == 1

    def test_missing_premise_is_warning(self, detector: FallacyDetector) -> None:
        chain = ChainBuilder("c1", "T").inference("i1", "Something.").build()
        result = detector.validate(chain)
        warnings = [i for i in result.issues if i.fallacy_type == FallacyType.MISSING_PREMISE]
        assert len(warnings) == 1
        assert warnings[0].severity == "warning"

    def test_missing_premise_does_not_fail_validity(self, detector: FallacyDetector) -> None:
        # Warnings should not invalidate the chain
        chain = ChainBuilder("c1", "T").inference("i1", "Something.").build()
        result = detector.validate(chain)
        # Only a warning-level issue; chain should be marked valid
        assert result.is_valid is True

    def test_circular_reasoning_detected(self, detector: FallacyDetector) -> None:
        chain = ReasoningChain(chain_id="c1", title="Circular")
        chain.add_step(
            ReasoningStep(step_id="s1", content="A", depends_on=["s2"])
        )
        chain.add_step(
            ReasoningStep(step_id="s2", content="B", depends_on=["s1"])
        )
        result = detector.validate(chain)
        cyclic = [
            i for i in result.issues if i.fallacy_type == FallacyType.CIRCULAR_REASONING
        ]
        assert len(cyclic) >= 1

    def test_multiple_broken_deps_all_reported(self, detector: FallacyDetector) -> None:
        chain = ReasoningChain(chain_id="c1", title="T")
        chain.add_step(
            ReasoningStep(step_id="s1", content="A", depends_on=["x1", "x2"])
        )
        result = detector.validate(chain)
        broken = [i for i in result.issues if i.fallacy_type == FallacyType.BROKEN_DEPENDENCY]
        assert len(broken) == 2

    def test_issue_ids_are_sequential(self, detector: FallacyDetector) -> None:
        chain = ChainBuilder("c1", "T").conclusion("c1", "Final.").build()
        result = detector.validate(chain)
        assert result.issues[0].issue_id == "issue_0001"

    def test_empty_chain_is_valid(self, detector: FallacyDetector) -> None:
        chain = ReasoningChain(chain_id="c1", title="Empty")
        result = detector.validate(chain)
        assert result.is_valid is True
        assert result.issues == []

    def test_premise_with_no_deps_is_fine(self, detector: FallacyDetector) -> None:
        chain = ChainBuilder("c1", "T").premise("p1", "Foundation.").build()
        result = detector.validate(chain)
        assert result.is_valid is True

    def test_validate_returns_chain_validation(self, detector: FallacyDetector) -> None:
        chain = ReasoningChain(chain_id="c1", title="T")
        result = detector.validate(chain)
        assert isinstance(result, ChainValidation)

    def test_chain_id_in_result(
        self, detector: FallacyDetector, simple_chain: ReasoningChain
    ) -> None:
        result = detector.validate(simple_chain)
        assert result.chain_id == "c1"


# ---------------------------------------------------------------------------
# ChainValidation model tests
# ---------------------------------------------------------------------------


class TestChainValidation:
    def test_errors_property_filters_errors(self) -> None:
        issues = [
            ValidationIssue(
                issue_id="i1",
                step_id="s1",
                fallacy_type=FallacyType.BROKEN_DEPENDENCY,
                message="err",
                severity="error",
            ),
            ValidationIssue(
                issue_id="i2",
                step_id="s2",
                fallacy_type=FallacyType.MISSING_PREMISE,
                message="warn",
                severity="warning",
            ),
        ]
        cv = ChainValidation(chain_id="c1", is_valid=False, issues=issues, step_count=2)
        assert len(cv.errors) == 1
        assert cv.errors[0].severity == "error"

    def test_warnings_property_filters_warnings(self) -> None:
        issues = [
            ValidationIssue(
                issue_id="i1",
                step_id="s1",
                fallacy_type=FallacyType.BROKEN_DEPENDENCY,
                message="err",
                severity="error",
            ),
            ValidationIssue(
                issue_id="i2",
                step_id="s2",
                fallacy_type=FallacyType.MISSING_PREMISE,
                message="warn",
                severity="warning",
            ),
        ]
        cv = ChainValidation(chain_id="c1", is_valid=False, issues=issues, step_count=2)
        assert len(cv.warnings) == 1
        assert cv.warnings[0].severity == "warning"

    def test_step_count_must_be_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            ChainValidation(chain_id="c1", is_valid=True, step_count=-1)

    def test_empty_issues_list(self) -> None:
        cv = ChainValidation(chain_id="c1", is_valid=True)
        assert cv.issues == []
        assert cv.errors == []
        assert cv.warnings == []


# ---------------------------------------------------------------------------
# FallacyType and StepType enum tests
# ---------------------------------------------------------------------------


class TestEnums:
    def test_fallacy_type_values(self) -> None:
        assert FallacyType.CIRCULAR_REASONING == "circular_reasoning"
        assert FallacyType.BROKEN_DEPENDENCY == "broken_dependency"
        assert FallacyType.UNSUPPORTED_CONCLUSION == "unsupported_conclusion"
        assert FallacyType.MISSING_PREMISE == "missing_premise"
        assert FallacyType.UNDEFINED_REFERENCE == "undefined_reference"

    def test_step_type_values(self) -> None:
        assert StepType.PREMISE == "premise"
        assert StepType.INFERENCE == "inference"
        assert StepType.CONCLUSION == "conclusion"
        assert StepType.ASSUMPTION == "assumption"
        assert StepType.EVIDENCE == "evidence"
        assert StepType.REBUTTAL == "rebuttal"

    def test_step_type_is_string_enum(self) -> None:
        assert isinstance(StepType.PREMISE, str)

    def test_fallacy_type_is_string_enum(self) -> None:
        assert isinstance(FallacyType.CIRCULAR_REASONING, str)


# ---------------------------------------------------------------------------
# End-to-end integration tests
# ---------------------------------------------------------------------------


class TestEndToEnd:
    def test_full_valid_chain(self) -> None:
        chain = (
            ChainBuilder("tax_arg", "Tax Argument")
            .premise("p1", "All citizens pay taxes.")
            .premise("p2", "Alice is a citizen.")
            .inference("i1", "Alice pays taxes.", depends_on=["p1", "p2"])
            .conclusion("c1", "Alice is a taxpayer.", depends_on=["i1"])
            .build()
        )
        detector = FallacyDetector()
        result = detector.validate(chain)
        assert result.is_valid is True

    def test_chain_with_evidence_and_rebuttal(self) -> None:
        chain = (
            ChainBuilder("arg2", "Complex Argument")
            .premise("p1", "X implies Y.")
            .evidence("e1", "Study A shows X.", depends_on=["p1"])
            .add_step("r1", "Counter: Y may not always follow.", StepType.REBUTTAL, depends_on=["e1"])
            .conclusion("c1", "Y is likely.", depends_on=["e1"])
            .build()
        )
        detector = FallacyDetector()
        result = detector.validate(chain)
        assert result.is_valid is True

    def test_mermaid_and_text_render_same_steps(self) -> None:
        chain = (
            ChainBuilder("c1", "Test")
            .premise("p1", "A")
            .conclusion("c1", "B", depends_on=["p1"])
            .build()
        )
        viz = ChainVisualizer()
        mermaid = viz.to_mermaid(chain)
        text = viz.to_text(chain)
        assert "p1" in mermaid
        assert "p1" in text

    def test_chain_serialization_round_trip(self, simple_chain: ReasoningChain) -> None:
        json_str = simple_chain.model_dump_json()
        restored = ReasoningChain.model_validate_json(json_str)
        assert restored.chain_id == simple_chain.chain_id
        assert len(restored.steps) == len(simple_chain.steps)

    def test_deeply_nested_chain(self) -> None:
        builder = ChainBuilder("deep", "Deep Chain")
        builder.premise("p0", "Root fact.")
        for i in range(1, 6):
            builder.inference(f"i{i}", f"Step {i}.", depends_on=[f"i{i-1}" if i > 1 else "p0"])
        builder.conclusion("c1", "Final.", depends_on=["i5"])
        chain = builder.build()
        detector = FallacyDetector()
        result = detector.validate(chain)
        assert result.is_valid is True
        assert result.step_count == 7

    def test_detect_cycles_three_node_cycle(self) -> None:
        chain = ReasoningChain(chain_id="c1", title="Cycle")
        chain.add_step(ReasoningStep(step_id="a", content="A", depends_on=["c"]))
        chain.add_step(ReasoningStep(step_id="b", content="B", depends_on=["a"]))
        chain.add_step(ReasoningStep(step_id="c", content="C", depends_on=["b"]))
        detector = FallacyDetector()
        cyclic = detector._detect_cycles(chain)
        assert len(cyclic) > 0
