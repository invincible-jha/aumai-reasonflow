"""Quickstart examples for aumai-reasonflow.

Run this file directly to verify your installation and see the library in action:

    python examples/quickstart.py

This file demonstrates:
  1. Building a simple syllogism chain
  2. Detecting logical fallacies (broken deps, circular reasoning)
  3. Building a complex multi-branch argument
  4. Rendering chains as Mermaid and text
  5. Saving and reloading chains from JSON
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from aumai_reasonflow.core import ChainBuilder, ChainVisualizer, FallacyDetector
from aumai_reasonflow.models import (
    ChainValidation,
    FallacyType,
    ReasoningChain,
    StepType,
)


# ---------------------------------------------------------------------------
# Demo 1: Simple syllogism
# ---------------------------------------------------------------------------


def demo_syllogism() -> None:
    """Build and validate the classic Socrates syllogism.

    Demonstrates:
    - ChainBuilder fluent API (.premise, .conclusion)
    - FallacyDetector.validate()
    - ChainVisualizer.to_text()
    """
    print("=" * 60)
    print("Demo 1: Classic Syllogism")
    print("=" * 60)

    chain = (
        ChainBuilder("syllogism", "Socrates is Mortal")
        .premise("p1", "All humans are mortal.")
        .premise("p2", "Socrates is human.")
        .conclusion("c1", "Socrates is mortal.", depends_on=["p1", "p2"])
        .build()
    )

    print(f"  Chain: '{chain.title}' ({len(chain.steps)} steps)")

    detector = FallacyDetector()
    validation: ChainValidation = detector.validate(chain)
    print(f"  Valid: {validation.is_valid}")
    print(f"  Errors: {len(validation.errors)}  Warnings: {len(validation.warnings)}")

    viz = ChainVisualizer()
    print("\n  Text representation:")
    for line in viz.to_text(chain).splitlines():
        print(f"    {line}")
    print()


# ---------------------------------------------------------------------------
# Demo 2: Fallacy detection
# ---------------------------------------------------------------------------


def demo_fallacy_detection() -> None:
    """Build chains with deliberate structural errors and detect them.

    Demonstrates:
    - CIRCULAR_REASONING detection
    - BROKEN_DEPENDENCY detection
    - UNSUPPORTED_CONCLUSION detection
    - MISSING_PREMISE warning
    """
    print("=" * 60)
    print("Demo 2: Fallacy Detection")
    print("=" * 60)

    detector = FallacyDetector()

    # ---- Case A: Circular reasoning ----
    print("  Case A: Circular reasoning (i1 depends on i2, i2 depends on i1)")
    chain_a = (
        ChainBuilder("cycle", "Circular Chain")
        .premise("p1", "Some base fact.")
        .inference("i1", "Circular inference 1.", depends_on=["i2"])
        .inference("i2", "Circular inference 2.", depends_on=["i1"])
        .conclusion("c1", "Final conclusion.", depends_on=["i1"])
        .build()
    )
    v_a = detector.validate(chain_a)
    print(f"  Valid: {v_a.is_valid}  Errors: {len(v_a.errors)}")
    for issue in v_a.errors:
        if issue.fallacy_type == FallacyType.CIRCULAR_REASONING:
            print(f"    [CIRCULAR] {issue.message}")

    # ---- Case B: Broken dependency ----
    print("\n  Case B: Broken dependency (step_id 'ghost' does not exist)")
    chain_b = (
        ChainBuilder("broken", "Broken Chain")
        .premise("p1", "Real premise.")
        .conclusion("c1", "Conclusion depending on ghost.", depends_on=["p1", "ghost"])
        .build()
    )
    v_b = detector.validate(chain_b)
    print(f"  Valid: {v_b.is_valid}  Errors: {len(v_b.errors)}")
    for issue in v_b.errors:
        if issue.fallacy_type == FallacyType.BROKEN_DEPENDENCY:
            print(f"    [BROKEN_DEP] {issue.message}")

    # ---- Case C: Unsupported conclusion ----
    print("\n  Case C: Unsupported conclusion (no depends_on)")
    chain_c = (
        ChainBuilder("unsupported", "Unsupported Conclusion")
        .premise("p1", "Some premise.")
        .conclusion("c1", "Conclusion from nowhere.")  # no depends_on
        .build()
    )
    v_c = detector.validate(chain_c)
    print(f"  Valid: {v_c.is_valid}  Errors: {len(v_c.errors)}")
    for issue in v_c.errors:
        print(f"    [{issue.fallacy_type.value.upper()}] {issue.message}")

    # ---- Case D: Missing premise (warning only) ----
    print("\n  Case D: Inference with no premise (warning, not error)")
    chain_d = (
        ChainBuilder("ungrounded", "Ungrounded Inference")
        .inference("i1", "This inference has no supporting steps.")
        .conclusion("c1", "Conclusion.", depends_on=["i1"])
        .build()
    )
    v_d = detector.validate(chain_d)
    print(f"  Valid: {v_d.is_valid}  Warnings: {len(v_d.warnings)}")
    for issue in v_d.warnings:
        print(f"    [WARN: {issue.fallacy_type.value}] {issue.message}")
    print()


# ---------------------------------------------------------------------------
# Demo 3: Multi-branch argument with all step types
# ---------------------------------------------------------------------------


def demo_complex_chain() -> None:
    """Build a realistic multi-branch credit-risk argument.

    Demonstrates:
    - All six step types: PREMISE, EVIDENCE, ASSUMPTION, INFERENCE, CONCLUSION
    - Confidence propagation display in to_text()
    - get_premises() and get_conclusions()
    """
    print("=" * 60)
    print("Demo 3: Multi-Branch Credit Risk Assessment")
    print("=" * 60)

    chain = (
        ChainBuilder("credit_risk", "Credit Risk Assessment",
                     description="Evaluating an applicant for a personal loan.")
        # Foundational policies
        .premise("p_policy", "Loan policy requires income > $50k and no defaults.")
        # Empirical evidence
        .evidence("e_income", "Payroll records show annual income of $72,000.",
                  confidence=0.99)
        .evidence("e_credit", "Credit bureau report: no defaults in 7 years.",
                  confidence=0.96)
        # An assumption about the future
        .assumption("a_stability", "Applicant's employment is expected to remain stable.",
                    confidence=0.70,
                    notes="Based on industry stability index; inherently uncertain.")
        # Inferences derived from evidence + policy
        .inference("i_income_ok", "Income threshold is satisfied.",
                   depends_on=["p_policy", "e_income"],
                   confidence=0.99)
        .inference("i_credit_ok", "Credit history threshold is satisfied.",
                   depends_on=["p_policy", "e_credit"],
                   confidence=0.96)
        .inference("i_qualifies", "Applicant meets all required loan criteria.",
                   depends_on=["i_income_ok", "i_credit_ok", "a_stability"],
                   confidence=0.88)
        # Final conclusion
        .conclusion("c_approve", "Approve loan application.",
                    depends_on=["i_qualifies"])
        .build()
    )

    print(f"  Chain: '{chain.title}' ({len(chain.steps)} steps)")
    print(f"  Premises:    {len(chain.get_premises())}")
    print(f"  Conclusions: {len(chain.get_conclusions())}")

    detector = FallacyDetector()
    validation = detector.validate(chain)
    print(f"  Valid: {validation.is_valid}")

    viz = ChainVisualizer()
    print("\n  Text representation:")
    for line in viz.to_text(chain).splitlines():
        print(f"    {line}")
    print()


# ---------------------------------------------------------------------------
# Demo 4: Mermaid diagram rendering
# ---------------------------------------------------------------------------


def demo_mermaid() -> None:
    """Render a chain as a Mermaid flowchart.

    Demonstrates:
    - ChainVisualizer.to_mermaid()
    - Type-differentiated node shapes
    """
    print("=" * 60)
    print("Demo 4: Mermaid Diagram Rendering")
    print("=" * 60)

    chain = (
        ChainBuilder("mermaid_demo", "Argument with All Step Types")
        .premise("p1", "Foundational premise.")
        .evidence("e1", "Supporting evidence.", depends_on=["p1"])
        .assumption("a1", "Uncertain assumption.", confidence=0.65)
        .inference("i1", "Derived inference.", depends_on=["p1", "e1", "a1"])
        .conclusion("c1", "Final conclusion.", depends_on=["i1"])
        .build()
    )

    viz = ChainVisualizer()
    mermaid = viz.to_mermaid(chain)
    print("  Mermaid diagram (paste into https://mermaid.live to render):\n")
    for line in mermaid.splitlines():
        print(f"    {line}")
    print()

    # Node shape reference
    print("  Node shape reference by step type:")
    print("    PREMISE     -> stadium   ([...])")
    print("    INFERENCE   -> rectangle [...]")
    print("    ASSUMPTION  -> diamond   {...}")
    print("    CONCLUSION  -> circle    ((...))")
    print("    EVIDENCE    -> parallelogram [/.../]")
    print("    REBUTTAL    -> reverse parallelogram")
    print()


# ---------------------------------------------------------------------------
# Demo 5: JSON round-trip persistence
# ---------------------------------------------------------------------------


def demo_json_persistence(tmp_dir: Path) -> None:
    """Save a reasoning chain to JSON and reload it.

    Demonstrates:
    - ReasoningChain.model_dump_json()
    - ReasoningChain.model_validate()
    - Validation after reload
    """
    print("=" * 60)
    print("Demo 5: JSON Persistence Round-Trip")
    print("=" * 60)

    # Build
    chain = (
        ChainBuilder("persist_demo", "Persistent Chain")
        .premise("p1", "All A are B.")
        .premise("p2", "All B are C.")
        .inference("i1", "All A are C.", depends_on=["p1", "p2"], confidence=0.99)
        .conclusion("c1", "Therefore A implies C.", depends_on=["i1"])
        .build()
    )

    # Save
    json_path = tmp_dir / "chain.json"
    json_path.write_text(chain.model_dump_json(indent=2), encoding="utf-8")
    print(f"  Saved chain to {json_path}")

    # Reload
    data = json.loads(json_path.read_text(encoding="utf-8"))
    loaded: ReasoningChain = ReasoningChain.model_validate(data)
    print(f"  Reloaded: '{loaded.title}' with {len(loaded.steps)} steps")

    # Re-validate after reload
    validation = FallacyDetector().validate(loaded)
    print(f"  Valid after reload: {validation.is_valid}")

    # Inspect a step
    step = loaded.steps["i1"]
    print(f"\n  Step 'i1':")
    print(f"    Content:    {step.content}")
    print(f"    Type:       {step.step_type.value}")
    print(f"    Depends on: {step.depends_on}")
    print(f"    Confidence: {step.confidence:.0%}")
    print()


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> None:
    """Run all quickstart demos in sequence."""
    print("\naumai-reasonflow Quickstart Demos")
    print("=" * 60)
    print()

    demo_syllogism()
    demo_fallacy_detection()
    demo_complex_chain()
    demo_mermaid()

    with tempfile.TemporaryDirectory() as tmp:
        demo_json_persistence(Path(tmp))

    print("All demos completed successfully.")


if __name__ == "__main__":
    main()
