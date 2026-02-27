# Getting Started with aumai-reasonflow

This guide takes you from installation to building, validating, and visualizing
reasoning chains in under 15 minutes.

---

## Prerequisites

- Python 3.11 or higher
- `pip` (standard) or `uv` (recommended)
- No prior knowledge of formal logic or argumentation theory is required

---

## Installation

### From PyPI (stable)

```bash
pip install aumai-reasonflow
```

### From source (development)

```bash
git clone https://github.com/AumAI/aumai-reasonflow
cd aumai-reasonflow
pip install -e ".[dev]"
```

### Verify the installation

```bash
aumai-reasonflow --version
# aumai-reasonflow, version 0.1.0

python -c "import aumai_reasonflow; print('OK')"
# OK
```

---

## Step-by-Step Tutorial

### Step 1: Build your first chain (Python API)

```python
from aumai_reasonflow.core import ChainBuilder

chain = (
    ChainBuilder("socrates", "Socrates is Mortal")
    .premise("p1", "All humans are mortal.")
    .premise("p2", "Socrates is human.")
    .conclusion("c1", "Socrates is mortal.", depends_on=["p1", "p2"])
    .build()
)

print(f"Chain ID: {chain.chain_id}")
print(f"Steps: {len(chain.steps)}")
```

### Step 2: Validate the chain

```python
from aumai_reasonflow.core import FallacyDetector

detector = FallacyDetector()
validation = detector.validate(chain)

print(f"Valid: {validation.is_valid}")        # True
print(f"Errors: {len(validation.errors)}")    # 0
print(f"Warnings: {len(validation.warnings)}")  # 0
```

### Step 3: Visualize as text

```python
from aumai_reasonflow.core import ChainVisualizer

viz = ChainVisualizer()
print(viz.to_text(chain))
```

Output:

```
Chain: Socrates is Mortal (id=socrates)

[PREMISE] [100%] p1: All humans are mortal.
[PREMISE] [100%] p2: Socrates is human.
  [CONCLUSION] [100%] c1: Socrates is mortal.
```

### Step 4: Export as Mermaid

```python
print(viz.to_mermaid(chain))
```

Output:

```
flowchart TD
    %% Socrates is Mortal
    p1(["All humans are mortal."])
    p2(["Socrates is human."])
    c1(("Socrates is mortal."))
    p1 --> c1
    p2 --> c1
```

Paste this into [Mermaid Live Editor](https://mermaid.live) to render the diagram.

### Step 5: Save and reload

```python
from pathlib import Path
from aumai_reasonflow.models import ReasoningChain
import json

# Save
Path("socrates.json").write_text(chain.model_dump_json(indent=2), encoding="utf-8")

# Load
data = json.loads(Path("socrates.json").read_text(encoding="utf-8"))
loaded = ReasoningChain.model_validate(data)
print(f"Loaded chain: {loaded.title}")
```

### Step 6: Build via JSON spec and CLI

Create `socrates_spec.json`:

```json
{
  "chain_id": "socrates",
  "title": "Socrates is Mortal",
  "steps": [
    {"step_id": "p1", "step_type": "premise",    "content": "All humans are mortal."},
    {"step_id": "p2", "step_type": "premise",    "content": "Socrates is human."},
    {"step_id": "c1", "step_type": "conclusion", "content": "Socrates is mortal.",
     "depends_on": ["p1", "p2"]}
  ]
}
```

```bash
aumai-reasonflow build --input socrates_spec.json --output socrates.json
aumai-reasonflow validate socrates.json
aumai-reasonflow visualize socrates.json --format mermaid
```

---

## Common Patterns and Recipes

### Pattern 1: Multi-branch argument with evidence

Model a real-world decision with multiple sources of evidence:

```python
from aumai_reasonflow.core import ChainBuilder, FallacyDetector, ChainVisualizer

chain = (
    ChainBuilder("loan_decision", "Loan Approval Decision")
    .premise("p_policy", "Loans require income > $50k and clean credit.")
    .evidence("e_income", "Applicant income verified at $72k.",
              confidence=0.98)
    .evidence("e_credit", "Credit bureau shows no defaults.",
              confidence=0.95)
    .inference("i_qualifies", "Applicant meets all loan criteria.",
               depends_on=["p_policy", "e_income", "e_credit"],
               confidence=0.93)
    .conclusion("c_approve", "Approve loan application.",
                depends_on=["i_qualifies"])
    .build()
)

detector = FallacyDetector()
validation = detector.validate(chain)
print(f"Valid: {validation.is_valid}")   # True

viz = ChainVisualizer()
print(viz.to_mermaid(chain))
```

### Pattern 2: Detecting circular reasoning

Build a deliberately broken chain to see fallacy detection in action:

```python
from aumai_reasonflow.core import ChainBuilder, FallacyDetector
from aumai_reasonflow.models import FallacyType

# Circular: i1 -> i2 -> i1
chain = (
    ChainBuilder("circular", "Circular Example")
    .premise("p1", "The sky is blue.")
    .inference("i1", "Inference 1.", depends_on=["i2"])
    .inference("i2", "Inference 2.", depends_on=["i1"])
    .conclusion("c1", "Conclusion.", depends_on=["i1"])
    .build()
)

validation = FallacyDetector().validate(chain)
print(f"Valid: {validation.is_valid}")   # False

for issue in validation.errors:
    print(f"[{issue.fallacy_type.value}] {issue.message}")
# [circular_reasoning] Step 'i1' is part of a circular dependency.
# [circular_reasoning] Step 'i2' is part of a circular dependency.
```

### Pattern 3: Including assumptions with lower confidence

```python
chain = (
    ChainBuilder("forecast", "Revenue Forecast")
    .evidence("e_q3", "Q3 revenue grew 12% YoY.", confidence=1.0)
    .assumption("a_trend", "Growth trend continues into Q4.",
                confidence=0.65, notes="Assumes no macro disruptions.")
    .inference("i_q4_growth", "Q4 revenue will grow ~12% YoY.",
               depends_on=["e_q3", "a_trend"], confidence=0.6)
    .conclusion("c_target", "Q4 target is achievable.",
                depends_on=["i_q4_growth"])
    .build()
)

from aumai_reasonflow.core import ChainVisualizer
print(ChainVisualizer().to_text(chain))
# The assumption's 65% confidence will be surfaced in the text output.
```

### Pattern 4: Batch validation in CI

Write a helper that validates all chain JSON files in a directory:

```python
import sys
from pathlib import Path
from aumai_reasonflow.core import FallacyDetector
from aumai_reasonflow.models import ReasoningChain
import json

def validate_all_chains(directory: Path) -> bool:
    detector = FallacyDetector()
    all_valid = True
    for chain_file in directory.glob("*.chain.json"):
        data = json.loads(chain_file.read_text(encoding="utf-8"))
        chain = ReasoningChain.model_validate(data)
        validation = detector.validate(chain)
        status = "VALID" if validation.is_valid else "INVALID"
        print(f"  [{status}] {chain_file.name}")
        if not validation.is_valid:
            all_valid = False
            for issue in validation.errors:
                print(f"    ERROR: {issue.message}")
    return all_valid

if not validate_all_chains(Path("chains/")):
    sys.exit(1)
```

### Pattern 5: Exporting Mermaid to a file for documentation

```python
from pathlib import Path
from aumai_reasonflow.core import ChainVisualizer
from aumai_reasonflow.models import ReasoningChain
import json

def export_mermaid(chain_json_path: Path, output_dir: Path) -> None:
    data = json.loads(chain_json_path.read_text(encoding="utf-8"))
    chain = ReasoningChain.model_validate(data)
    viz = ChainVisualizer()
    mermaid = viz.to_mermaid(chain)
    out_path = output_dir / f"{chain.chain_id}.mmd"
    out_path.write_text(mermaid, encoding="utf-8")
    print(f"Exported Mermaid diagram to {out_path}")

export_mermaid(Path("socrates.json"), Path("diagrams/"))
```

---

## Troubleshooting FAQ

**Q: `FallacyDetector.validate` reports `is_valid=False` with no error issues.**

A: `is_valid` is `True` only when there are zero *error*-severity issues.
Check `validation.warnings` — it is possible the chain has warning-only issues
(e.g., inference steps with no dependencies). These are reported but do not
make the chain invalid.

**Q: `ChainBuilder` raises `ValueError: Step 'X' already exists in chain.`**

A: Each `step_id` must be unique within a chain. If you are building chains
programmatically from a loop, ensure you generate unique IDs (e.g., `step_0`,
`step_1`, etc.).

**Q: `to_text` shows my steps in a strange order.**

A: The text renderer uses topological sort. Steps appear in dependency order:
roots (no dependencies) first, then their dependents. If your chain has a
cycle, the sort may be incomplete — validate first with `FallacyDetector`.

**Q: Mermaid output looks wrong in my renderer.**

A: Step IDs containing hyphens, dots, or spaces are sanitized by replacing
them with underscores. If two different step IDs sanitize to the same string,
they will be merged in the Mermaid output. Use only alphanumeric characters
and underscores in step IDs to avoid this.

**Q: `build` CLI command skips some steps with "WARNING: skipping invalid step".**

A: The `build` command silently skips steps with malformed fields. Check that
`step_id` and `content` are non-empty strings and that `step_type` is one of:
`premise`, `inference`, `assumption`, `conclusion`, `evidence`, `rebuttal`.

**Q: How do I represent "A OR B supports conclusion C"?**

A: The current model only supports conjunctive `depends_on` lists (all
dependencies must hold). Disjunctive support is not yet expressible in a
single `ReasoningStep`. A workaround is to split into two separate chains or
use an intermediate inference step that explicitly describes the OR logic
in its `content` and `notes`.

---

## Next Steps

- Read the [API Reference](api-reference.md) for complete class/method documentation
- Explore [examples/quickstart.py](../examples/quickstart.py) for runnable demos
- Integrate with [aumai-neurosymbolic](https://github.com/AumAI/aumai-neurosymbolic)
  to verify reasoning chains symbolically
- Join the [Discord community](https://discord.gg/aumai)
