"""Core logic for the visual reasoning chain editor and debugger.

Provides:
- ChainBuilder: fluent API for constructing ReasoningChain objects.
- ChainVisualizer: render a chain as Mermaid diagrams or plain text.
- FallacyDetector: detect logical fallacies and broken dependencies.
"""

from __future__ import annotations

from typing import Optional

from .models import (
    ChainValidation,
    FallacyType,
    ReasoningChain,
    ReasoningStep,
    StepType,
    ValidationIssue,
)


# ---------------------------------------------------------------------------
# ChainBuilder
# ---------------------------------------------------------------------------


class ChainBuilder:
    """Fluent builder for ReasoningChain objects.

    Example:
        >>> chain = (
        ...     ChainBuilder("chain_1", "Tax Argument")
        ...     .premise("p1", "All citizens pay taxes.")
        ...     .premise("p2", "Alice is a citizen.")
        ...     .inference("i1", "Alice pays taxes.", depends_on=["p1", "p2"])
        ...     .conclusion("c1", "Alice is a taxpayer.", depends_on=["i1"])
        ...     .build()
        ... )
    """

    def __init__(self, chain_id: str, title: str, description: Optional[str] = None) -> None:
        """Initialise the builder.

        Args:
            chain_id: Unique ID for the chain.
            title: Short title for the chain.
            description: Optional longer description.
        """
        self._chain = ReasoningChain(
            chain_id=chain_id, title=title, description=description
        )
        self._issue_counter = 0

    def add_step(
        self,
        step_id: str,
        content: str,
        step_type: StepType,
        depends_on: Optional[list[str]] = None,
        confidence: float = 1.0,
        notes: Optional[str] = None,
    ) -> "ChainBuilder":
        """Add a generic step to the chain.

        Args:
            step_id: Unique identifier for this step.
            content: Natural-language statement.
            step_type: Type classification.
            depends_on: List of step IDs this step depends on.
            confidence: Confidence level in [0, 1].
            notes: Optional annotations.

        Returns:
            Self, for method chaining.
        """
        self._chain.add_step(
            ReasoningStep(
                step_id=step_id,
                content=content,
                step_type=step_type,
                depends_on=depends_on or [],
                confidence=confidence,
                notes=notes,
            )
        )
        return self

    def premise(
        self,
        step_id: str,
        content: str,
        confidence: float = 1.0,
        notes: Optional[str] = None,
    ) -> "ChainBuilder":
        """Add a PREMISE step."""
        return self.add_step(step_id, content, StepType.PREMISE, confidence=confidence, notes=notes)

    def inference(
        self,
        step_id: str,
        content: str,
        depends_on: Optional[list[str]] = None,
        confidence: float = 1.0,
        notes: Optional[str] = None,
    ) -> "ChainBuilder":
        """Add an INFERENCE step."""
        return self.add_step(
            step_id, content, StepType.INFERENCE, depends_on=depends_on, confidence=confidence, notes=notes
        )

    def conclusion(
        self,
        step_id: str,
        content: str,
        depends_on: Optional[list[str]] = None,
        confidence: float = 1.0,
        notes: Optional[str] = None,
    ) -> "ChainBuilder":
        """Add a CONCLUSION step."""
        return self.add_step(
            step_id, content, StepType.CONCLUSION, depends_on=depends_on, confidence=confidence, notes=notes
        )

    def assumption(
        self,
        step_id: str,
        content: str,
        confidence: float = 0.8,
        notes: Optional[str] = None,
    ) -> "ChainBuilder":
        """Add an ASSUMPTION step."""
        return self.add_step(step_id, content, StepType.ASSUMPTION, confidence=confidence, notes=notes)

    def evidence(
        self,
        step_id: str,
        content: str,
        depends_on: Optional[list[str]] = None,
        confidence: float = 1.0,
        notes: Optional[str] = None,
    ) -> "ChainBuilder":
        """Add an EVIDENCE step."""
        return self.add_step(
            step_id, content, StepType.EVIDENCE, depends_on=depends_on, confidence=confidence, notes=notes
        )

    def build(self) -> ReasoningChain:
        """Finalise and return the constructed chain.

        Returns:
            The assembled ReasoningChain.
        """
        return self._chain


# ---------------------------------------------------------------------------
# ChainVisualizer
# ---------------------------------------------------------------------------


class ChainVisualizer:
    """Render a ReasoningChain as Mermaid or plain text.

    Example:
        >>> viz = ChainVisualizer()
        >>> print(viz.to_mermaid(chain))
        >>> print(viz.to_text(chain))
    """

    # Mermaid shape per step type
    _MERMAID_SHAPES: dict[StepType, tuple[str, str]] = {
        StepType.PREMISE: ("([", "])"),
        StepType.INFERENCE: ("[", "]"),
        StepType.ASSUMPTION: ("{", "}"),
        StepType.CONCLUSION: ("((", "))"),
        StepType.EVIDENCE: ("[/", "/]"),
        StepType.REBUTTAL: ("[\\ ", " \\]"),
    }

    def to_mermaid(self, chain: ReasoningChain) -> str:
        """Render the chain as a Mermaid flowchart (top-down).

        Args:
            chain: The ReasoningChain to render.

        Returns:
            Mermaid diagram string.
        """
        lines: list[str] = [f"flowchart TD", f"    %% {chain.title}"]

        for step_id, step in chain.steps.items():
            safe_id = self._safe_id(step_id)
            label = self._truncate(step.content, 40)
            open_shape, close_shape = self._MERMAID_SHAPES.get(
                step.step_type, ("[", "]")
            )
            lines.append(f'    {safe_id}{open_shape}"{label}"{close_shape}')

        # Edges
        for step_id, step in chain.steps.items():
            safe_id = self._safe_id(step_id)
            for dep_id in step.depends_on:
                safe_dep = self._safe_id(dep_id)
                lines.append(f"    {safe_dep} --> {safe_id}")

        return "\n".join(lines)

    def to_text(self, chain: ReasoningChain, indent: str = "  ") -> str:
        """Render the chain as an indented text outline.

        Args:
            chain: The ReasoningChain to render.
            indent: Indentation string per dependency level.

        Returns:
            Plain-text representation.
        """
        lines: list[str] = [
            f"Chain: {chain.title} (id={chain.chain_id})",
        ]
        if chain.description:
            lines.append(f"Description: {chain.description}")
        lines.append("")

        # Topological order
        ordered = self._topological_sort(chain)

        for step in ordered:
            depth = self._depth(step.step_id, chain)
            prefix = indent * depth
            conf_str = f"[{step.confidence:.0%}]"
            lines.append(
                f"{prefix}[{step.step_type.value.upper()}] {conf_str} {step.step_id}: {step.content}"
            )
            if step.notes:
                lines.append(f"{prefix}  NOTE: {step.notes}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _safe_id(self, step_id: str) -> str:
        """Convert a step_id to a Mermaid-safe identifier."""
        return step_id.replace("-", "_").replace(".", "_").replace(" ", "_")

    def _truncate(self, text: str, max_len: int) -> str:
        """Truncate text to max_len with ellipsis if needed."""
        return text if len(text) <= max_len else text[: max_len - 3] + "..."

    def _depth(
        self,
        step_id: str,
        chain: ReasoningChain,
        visited: set[str] | None = None,
    ) -> int:
        """Compute the dependency depth of a step (0 = no dependencies).

        Args:
            step_id: The step whose depth to compute.
            chain: The containing ReasoningChain.
            visited: Set of step IDs already on the current recursion path,
                used to break cycles and prevent infinite recursion.

        Returns:
            Integer depth; 0 means the step has no dependencies.
        """
        if visited is None:
            visited = set()
        if step_id in visited:
            return 0
        step = chain.steps.get(step_id)
        if not step or not step.depends_on:
            return 0
        visited = visited | {step_id}
        return 1 + max(self._depth(dep, chain, visited) for dep in step.depends_on)

    def _topological_sort(self, chain: ReasoningChain) -> list[ReasoningStep]:
        """Return steps in topological (dependency-first) order."""
        visited: set[str] = set()
        result: list[ReasoningStep] = []

        def visit(step_id: str) -> None:
            if step_id in visited:
                return
            visited.add(step_id)
            step = chain.steps.get(step_id)
            if step is None:
                return
            for dep_id in step.depends_on:
                visit(dep_id)
            result.append(step)

        for sid in chain.steps:
            visit(sid)
        return result


# ---------------------------------------------------------------------------
# FallacyDetector
# ---------------------------------------------------------------------------


class FallacyDetector:
    """Detect logical fallacies and structural problems in a reasoning chain.

    Checks performed:
    - Circular reasoning: dependency cycles.
    - Undefined references: depends_on IDs that don't exist in the chain.
    - Unsupported conclusions: CONCLUSION steps with no dependencies.
    - Missing premises: INFERENCE steps that depend on no premises or evidence.
    - Broken dependencies: edges to non-existent step IDs.

    Example:
        >>> detector = FallacyDetector()
        >>> validation = detector.validate(chain)
        >>> validation.is_valid
        True
    """

    def validate(self, chain: ReasoningChain) -> ChainValidation:
        """Validate a reasoning chain and return all detected issues.

        Args:
            chain: The ReasoningChain to validate.

        Returns:
            ChainValidation describing validity and all issues found.
        """
        issues: list[ValidationIssue] = []
        issue_counter = 0

        def add_issue(
            step_id: str, fallacy: FallacyType, message: str, severity: str = "error"
        ) -> None:
            nonlocal issue_counter
            issue_counter += 1
            issues.append(
                ValidationIssue(
                    issue_id=f"issue_{issue_counter:04d}",
                    step_id=step_id,
                    fallacy_type=fallacy,
                    message=message,
                    severity=severity,
                )
            )

        # 1. Broken / undefined references
        all_ids = set(chain.steps.keys())
        for step_id, step in chain.steps.items():
            for dep_id in step.depends_on:
                if dep_id not in all_ids:
                    add_issue(
                        step_id,
                        FallacyType.BROKEN_DEPENDENCY,
                        f"Step '{step_id}' depends on unknown step '{dep_id}'.",
                    )

        # 2. Circular reasoning (DFS cycle detection)
        cyclic_steps = self._detect_cycles(chain)
        for step_id in cyclic_steps:
            add_issue(
                step_id,
                FallacyType.CIRCULAR_REASONING,
                f"Step '{step_id}' is part of a circular dependency.",
            )

        # 3. Unsupported conclusions
        for step_id, step in chain.steps.items():
            if step.step_type == StepType.CONCLUSION and not step.depends_on:
                add_issue(
                    step_id,
                    FallacyType.UNSUPPORTED_CONCLUSION,
                    f"Conclusion '{step_id}' has no supporting steps.",
                )

        # 4. Inference steps with no grounding (warning only)
        for step_id, step in chain.steps.items():
            if step.step_type == StepType.INFERENCE and not step.depends_on:
                add_issue(
                    step_id,
                    FallacyType.MISSING_PREMISE,
                    f"Inference '{step_id}' has no premise or evidence dependencies.",
                    severity="warning",
                )

        errors = [i for i in issues if i.severity == "error"]
        return ChainValidation(
            chain_id=chain.chain_id,
            is_valid=len(errors) == 0,
            issues=issues,
            step_count=len(chain.steps),
        )

    def _detect_cycles(self, chain: ReasoningChain) -> set[str]:
        """Return the set of step IDs involved in dependency cycles.

        When a back-edge to a GRAY ancestor is found, all nodes on the current
        DFS path from that ancestor to the current node are added to the cyclic
        set, not just the ancestor itself.
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        colors: dict[str, int] = {sid: WHITE for sid in chain.steps}
        cyclic: set[str] = set()
        # path_stack tracks the current DFS path for cycle-member extraction
        path_stack: list[str] = []

        def dfs(step_id: str) -> None:
            if step_id not in colors:
                return
            if colors[step_id] == GRAY:
                # Back-edge found: add all nodes in the cycle (from the ancestor
                # to the current end of the path stack).
                ancestor_index = path_stack.index(step_id)
                for node_in_cycle in path_stack[ancestor_index:]:
                    cyclic.add(node_in_cycle)
                return
            if colors[step_id] == BLACK:
                return
            colors[step_id] = GRAY
            path_stack.append(step_id)
            step = chain.steps.get(step_id)
            if step:
                for dep_id in step.depends_on:
                    dfs(dep_id)
            path_stack.pop()
            colors[step_id] = BLACK

        for sid in chain.steps:
            if colors[sid] == WHITE:
                dfs(sid)
        return cyclic
