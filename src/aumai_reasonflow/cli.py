"""CLI entry point for aumai-reasonflow.

Commands:
    build     -- interactively build a reasoning chain from stdin JSON
    validate  -- validate an existing chain JSON file
    visualize -- render a chain as Mermaid or text
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from .core import ChainBuilder, ChainVisualizer, FallacyDetector
from .models import ReasoningChain, StepType


@click.group()
@click.version_option()
def main() -> None:
    """AumAI ReasonFlow -- visual reasoning chain editor and debugger."""


@main.command("build")
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to a JSON chain spec file.",
)
@click.option(
    "--output",
    "output_path",
    default=None,
    type=click.Path(path_type=Path),
    help="Output JSON path. Defaults to <input>.chain.json.",
)
def build_command(input_path: Path, output_path: Path | None) -> None:
    """Build a ReasoningChain from a JSON specification file.

    The spec file should be a JSON object with keys:
        chain_id, title, description (optional), steps (list of step objects).

    Example:

        aumai-reasonflow build --input spec.json --output chain.json
    """
    raw = json.loads(input_path.read_text(encoding="utf-8"))
    chain_id = raw.get("chain_id", "chain_1")
    title = raw.get("title", "Untitled Chain")
    description = raw.get("description")

    builder = ChainBuilder(chain_id=chain_id, title=title, description=description)

    for step_spec in raw.get("steps", []):
        try:
            step_type = StepType(step_spec.get("step_type", "inference"))
            builder.add_step(
                step_id=step_spec["step_id"],
                content=step_spec["content"],
                step_type=step_type,
                depends_on=step_spec.get("depends_on", []),
                confidence=step_spec.get("confidence", 1.0),
                notes=step_spec.get("notes"),
            )
        except Exception as exc:
            click.echo(f"WARNING: skipping invalid step: {exc}", err=True)

    chain = builder.build()
    dest = output_path or input_path.with_suffix(".chain.json")
    dest.write_text(chain.model_dump_json(indent=2), encoding="utf-8")
    click.echo(f"Built chain '{chain.title}' with {len(chain.steps)} step(s) -> {dest}")


@main.command("validate")
@click.argument("chain_file", type=click.Path(exists=True, path_type=Path))
def validate_command(chain_file: Path) -> None:
    """Validate a reasoning chain JSON file for logical fallacies.

    CHAIN_FILE: Path to a saved ReasoningChain JSON file.

    Example:

        aumai-reasonflow validate chain.json
    """
    try:
        data = json.loads(chain_file.read_text(encoding="utf-8"))
        chain = ReasoningChain.model_validate(data)
    except Exception as exc:
        click.echo(f"ERROR loading chain: {exc}", err=True)
        sys.exit(1)

    detector = FallacyDetector()
    validation = detector.validate(chain)

    status = "VALID" if validation.is_valid else "INVALID"
    click.echo(f"Chain '{chain.title}': {status}")
    click.echo(f"Steps: {validation.step_count}  Errors: {len(validation.errors)}  Warnings: {len(validation.warnings)}")

    for issue in validation.issues:
        icon = "ERROR" if issue.severity == "error" else "WARN "
        click.echo(f"  [{icon}] {issue.step_id}: {issue.message}")

    if not validation.is_valid:
        sys.exit(1)


@main.command("visualize")
@click.argument("chain_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--format",
    "output_format",
    default="text",
    show_default=True,
    type=click.Choice(["text", "mermaid"], case_sensitive=False),
    help="Output format.",
)
@click.option(
    "--output",
    "output_path",
    default=None,
    type=click.Path(path_type=Path),
    help="Write output to file instead of stdout.",
)
def visualize_command(
    chain_file: Path, output_format: str, output_path: Path | None
) -> None:
    """Render a reasoning chain as Mermaid or plain text.

    CHAIN_FILE: Path to a saved ReasoningChain JSON file.

    Example:

        aumai-reasonflow visualize chain.json --format mermaid
    """
    try:
        data = json.loads(chain_file.read_text(encoding="utf-8"))
        chain = ReasoningChain.model_validate(data)
    except Exception as exc:
        click.echo(f"ERROR loading chain: {exc}", err=True)
        sys.exit(1)

    viz = ChainVisualizer()
    rendered = viz.to_mermaid(chain) if output_format == "mermaid" else viz.to_text(chain)

    if output_path:
        output_path.write_text(rendered, encoding="utf-8")
        click.echo(f"Wrote {output_format} diagram to {output_path}")
    else:
        click.echo(rendered)


if __name__ == "__main__":
    main()
