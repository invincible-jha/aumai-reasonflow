"""Pydantic v2 models for the reasoning chain editor."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class StepType(str, Enum):
    """Categorical type for a reasoning step."""

    PREMISE = "premise"
    INFERENCE = "inference"
    ASSUMPTION = "assumption"
    CONCLUSION = "conclusion"
    EVIDENCE = "evidence"
    REBUTTAL = "rebuttal"


class ReasoningStep(BaseModel):
    """A single node in a reasoning chain.

    Attributes:
        step_id: Unique identifier within the chain.
        content: The natural-language statement of this step.
        step_type: Categorical role of this step.
        depends_on: IDs of steps this step logically follows from.
        confidence: Author-assigned confidence in [0, 1].
        notes: Optional explanatory annotations.
    """

    step_id: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    step_type: StepType = StepType.INFERENCE
    depends_on: list[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    notes: Optional[str] = None

    @field_validator("step_id", "content")
    @classmethod
    def strip_whitespace(cls, value: str) -> str:
        """Strip surrounding whitespace."""
        return value.strip()


class ReasoningChain(BaseModel):
    """An ordered directed acyclic graph of reasoning steps.

    Attributes:
        chain_id: Unique identifier for the chain.
        title: Short human-readable title.
        steps: All reasoning steps indexed by step_id.
        description: Optional longer description of the argument.
    """

    chain_id: str
    title: str
    steps: dict[str, ReasoningStep] = Field(default_factory=dict)
    description: Optional[str] = None

    def add_step(self, step: ReasoningStep) -> None:
        """Add a step to the chain.

        Args:
            step: The ReasoningStep to add.

        Raises:
            ValueError: If a step with the same ID already exists.
        """
        if step.step_id in self.steps:
            raise ValueError(f"Step '{step.step_id}' already exists in chain.")
        self.steps[step.step_id] = step

    def get_conclusions(self) -> list[ReasoningStep]:
        """Return all steps of type CONCLUSION."""
        return [s for s in self.steps.values() if s.step_type == StepType.CONCLUSION]

    def get_premises(self) -> list[ReasoningStep]:
        """Return all steps of type PREMISE."""
        return [s for s in self.steps.values() if s.step_type == StepType.PREMISE]


class FallacyType(str, Enum):
    """Known logical fallacy types detectable by the engine."""

    CIRCULAR_REASONING = "circular_reasoning"
    UNDEFINED_REFERENCE = "undefined_reference"
    UNSUPPORTED_CONCLUSION = "unsupported_conclusion"
    MISSING_PREMISE = "missing_premise"
    BROKEN_DEPENDENCY = "broken_dependency"


class ValidationIssue(BaseModel):
    """A single validation issue found in a reasoning chain.

    Attributes:
        issue_id: Auto-assigned sequential identifier.
        step_id: The step where the issue was detected.
        fallacy_type: Categorical fallacy type.
        message: Human-readable description of the issue.
        severity: "error" or "warning".
    """

    issue_id: str
    step_id: str
    fallacy_type: FallacyType
    message: str
    severity: str = Field(default="error", pattern="^(error|warning)$")


class ChainValidation(BaseModel):
    """The result of validating a reasoning chain.

    Attributes:
        chain_id: ID of the chain that was validated.
        is_valid: True only if no error-severity issues exist.
        issues: All detected issues.
        step_count: Total number of steps validated.
    """

    chain_id: str
    is_valid: bool
    issues: list[ValidationIssue] = Field(default_factory=list)
    step_count: int = Field(default=0, ge=0)

    @property
    def errors(self) -> list[ValidationIssue]:
        """Return only error-severity issues."""
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        """Return only warning-severity issues."""
        return [i for i in self.issues if i.severity == "warning"]
