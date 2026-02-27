# API Reference — aumai-reasonflow

Complete reference for all public classes, methods, and Pydantic models in
`aumai_reasonflow`. All classes are importable from their module paths shown
below.

---

## Module: `aumai_reasonflow.models`

### `StepType`

```python
class StepType(str, Enum):
```

Categorical type for a reasoning step.

| Value | String | Description |
|---|---|---|
| `StepType.PREMISE` | `"premise"` | A foundational assertion accepted without proof |
| `StepType.INFERENCE` | `"inference"` | A derived statement following from other steps |
| `StepType.ASSUMPTION` | `"assumption"` | An unverified supposition (lower confidence) |
| `StepType.CONCLUSION` | `"conclusion"` | The final claim supported by the chain |
| `StepType.EVIDENCE` | `"evidence"` | An empirical observation or data point |
| `StepType.REBUTTAL` | `"rebuttal"` | A counter-argument (defined; not yet given special validation treatment) |

**Example:**

```python
from aumai_reasonflow.models import StepType

print(StepType.PREMISE.value)   # "premise"
print(StepType.CONCLUSION)      # StepType.CONCLUSION
```

---

### `ReasoningStep`

```python
class ReasoningStep(BaseModel):
```

A single node in a reasoning chain — one statement in an argument.

**Fields:**

| Field | Type | Required | Default | Constraints | Description |
|---|---|---|---|---|---|
| `step_id` | `str` | Yes | — | `min_length=1` | Unique identifier within the chain |
| `content` | `str` | Yes | — | `min_length=1` | The natural-language statement of this step |
| `step_type` | `StepType` | No | `StepType.INFERENCE` | — | Categorical role of this step |
| `depends_on` | `list[str]` | No | `[]` | — | IDs of steps this step logically follows from |
| `confidence` | `float` | No | `1.0` | `ge=0.0, le=1.0` | Author-assigned confidence in this step |
| `notes` | `Optional[str]` | No | `None` | — | Optional explanatory annotations |

**Validators:**

- `strip_whitespace`: strips surrounding whitespace from `step_id` and
  `content`

**Example:**

```python
from aumai_reasonflow.models import ReasoningStep, StepType

step = ReasoningStep(
    step_id="i1",
    content="Therefore, all A are C.",
    step_type=StepType.INFERENCE,
    depends_on=["p1", "p2"],
    confidence=0.95,
    notes="Follows by transitivity.",
)
```

---

### `ReasoningChain`

```python
class ReasoningChain(BaseModel):
```

An ordered directed acyclic graph of reasoning steps. The `steps` dictionary
preserves insertion order.

**Fields:**

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `chain_id` | `str` | Yes | — | Unique identifier for the chain |
| `title` | `str` | Yes | — | Short human-readable title |
| `steps` | `dict[str, ReasoningStep]` | No | `{}` | All reasoning steps indexed by `step_id` |
| `description` | `Optional[str]` | No | `None` | Optional longer description of the argument |

**Methods:**

#### `add_step(step: ReasoningStep) -> None`

Add a step to the chain.

**Parameters:**
- `step` — the `ReasoningStep` to add

**Raises:**
- `ValueError` if a step with the same `step_id` already exists in the chain

**Example:**

```python
from aumai_reasonflow.models import ReasoningChain, ReasoningStep, StepType

chain = ReasoningChain(chain_id="c1", title="Test Chain")
chain.add_step(ReasoningStep(step_id="p1", content="Premise 1.",
                              step_type=StepType.PREMISE))
```

#### `get_conclusions() -> list[ReasoningStep]`

Return all steps of type `CONCLUSION`.

**Returns:**
- `list[ReasoningStep]` — possibly empty

#### `get_premises() -> list[ReasoningStep]`

Return all steps of type `PREMISE`.

**Returns:**
- `list[ReasoningStep]` — possibly empty

---

### `FallacyType`

```python
class FallacyType(str, Enum):
```

Known logical fallacy types detectable by `FallacyDetector`.

| Value | String | When detected |
|---|---|---|
| `FallacyType.CIRCULAR_REASONING` | `"circular_reasoning"` | Step is part of a dependency cycle |
| `FallacyType.UNDEFINED_REFERENCE` | `"undefined_reference"` | Step references an undefined ID (reserved) |
| `FallacyType.UNSUPPORTED_CONCLUSION` | `"unsupported_conclusion"` | `CONCLUSION` step has empty `depends_on` |
| `FallacyType.MISSING_PREMISE` | `"missing_premise"` | `INFERENCE` step has empty `depends_on` (warning only) |
| `FallacyType.BROKEN_DEPENDENCY` | `"broken_dependency"` | `depends_on` contains an ID not in the chain |

---

### `ValidationIssue`

```python
class ValidationIssue(BaseModel):
```

A single validation issue found in a reasoning chain.

**Fields:**

| Field | Type | Required | Default | Constraints | Description |
|---|---|---|---|---|---|
| `issue_id` | `str` | Yes | — | — | Auto-assigned sequential identifier (e.g. `"issue_0001"`) |
| `step_id` | `str` | Yes | — | — | The step where the issue was detected |
| `fallacy_type` | `FallacyType` | Yes | — | — | Categorical fallacy type |
| `message` | `str` | Yes | — | — | Human-readable description of the issue |
| `severity` | `str` | No | `"error"` | `pattern="^(error\|warning)$"` | `"error"` or `"warning"` |

---

### `ChainValidation`

```python
class ChainValidation(BaseModel):
```

The result of validating a reasoning chain.

**Fields:**

| Field | Type | Required | Default | Constraints | Description |
|---|---|---|---|---|---|
| `chain_id` | `str` | Yes | — | — | ID of the chain that was validated |
| `is_valid` | `bool` | Yes | — | — | `True` only if no error-severity issues exist |
| `issues` | `list[ValidationIssue]` | No | `[]` | — | All detected issues (both errors and warnings) |
| `step_count` | `int` | No | `0` | `ge=0` | Total number of steps validated |

**Properties:**

#### `errors -> list[ValidationIssue]`

Return only error-severity issues.

#### `warnings -> list[ValidationIssue]`

Return only warning-severity issues.

**Example:**

```python
validation = detector.validate(chain)
print(f"Errors:   {len(validation.errors)}")
print(f"Warnings: {len(validation.warnings)}")
```

---

## Module: `aumai_reasonflow.core`

### `ChainBuilder`

```python
class ChainBuilder:
```

Fluent builder for `ReasoningChain` objects. All step-adding methods return
`self` for method chaining.

#### `__init__(chain_id: str, title: str, description: Optional[str] = None) -> None`

**Parameters:**
- `chain_id` — unique ID for the chain
- `title` — short title
- `description` — optional longer description (default: `None`)

#### `add_step(step_id, content, step_type, depends_on=None, confidence=1.0, notes=None) -> ChainBuilder`

Add a generic step to the chain.

**Parameters:**
- `step_id` — unique identifier for this step within the chain
- `content` — natural-language statement
- `step_type` — `StepType` enum value
- `depends_on` — list of step IDs this step depends on (default: `[]`)
- `confidence` — confidence level in `[0, 1]` (default: `1.0`)
- `notes` — optional annotation string (default: `None`)

**Returns:** `self` for chaining

**Raises:**
- `ValueError` if a step with the same `step_id` already exists

#### `premise(step_id, content, confidence=1.0, notes=None) -> ChainBuilder`

Add a `PREMISE` step. Premises have no dependencies.

#### `inference(step_id, content, depends_on=None, confidence=1.0, notes=None) -> ChainBuilder`

Add an `INFERENCE` step. Should depend on at least one other step.

#### `conclusion(step_id, content, depends_on=None, confidence=1.0, notes=None) -> ChainBuilder`

Add a `CONCLUSION` step. Should depend on at least one other step.

#### `assumption(step_id, content, confidence=0.8, notes=None) -> ChainBuilder`

Add an `ASSUMPTION` step. Default confidence is `0.8` to reflect the inherent
uncertainty of unverified suppositions.

#### `evidence(step_id, content, depends_on=None, confidence=1.0, notes=None) -> ChainBuilder`

Add an `EVIDENCE` step.

#### `build() -> ReasoningChain`

Finalise and return the constructed chain.

**Returns:** The assembled `ReasoningChain`

**Example:**

```python
from aumai_reasonflow.core import ChainBuilder

chain = (
    ChainBuilder("arg_1", "Simple Argument", description="A basic syllogism.")
    .premise("p1", "All humans are mortal.")
    .premise("p2", "Socrates is human.")
    .conclusion("c1", "Socrates is mortal.", depends_on=["p1", "p2"])
    .build()
)
print(chain.chain_id)    # "arg_1"
print(len(chain.steps))  # 3
```

---

### `ChainVisualizer`

```python
class ChainVisualizer:
```

Render a `ReasoningChain` as Mermaid or plain text.

#### `to_mermaid(chain: ReasoningChain) -> str`

Render the chain as a Mermaid flowchart (`flowchart TD`).

Node shapes are assigned by `StepType`:

| StepType | Mermaid | Shape |
|---|---|---|
| `PREMISE` | `([ ... ])` | Stadium |
| `INFERENCE` | `[ ... ]` | Rectangle |
| `ASSUMPTION` | `{ ... }` | Diamond |
| `CONCLUSION` | `(( ... ))` | Circle |
| `EVIDENCE` | `[/ ... /]` | Parallelogram |
| `REBUTTAL` | `[\ ... \]` | Reverse parallelogram |

Step IDs are sanitized: hyphens, dots, and spaces are replaced with underscores.
Content is truncated to 40 characters with ellipsis.

**Parameters:**
- `chain` — the `ReasoningChain` to render

**Returns:** Mermaid diagram string

**Example:**

```python
from aumai_reasonflow.core import ChainVisualizer

viz = ChainVisualizer()
print(viz.to_mermaid(chain))
# flowchart TD
#     %% Simple Argument
#     p1(["All humans are mortal."])
#     p2(["Socrates is human."])
#     c1(("Socrates is mortal."))
#     p1 --> c1
#     p2 --> c1
```

#### `to_text(chain: ReasoningChain, indent: str = "  ") -> str`

Render the chain as an indented text outline in topological order.

Each step is displayed as:

```
[TYPE] [CONFIDENCE%] step_id: content
  NOTE: notes
```

Depth indentation is computed from the maximum dependency depth.

**Parameters:**
- `chain` — the `ReasoningChain` to render
- `indent` — indentation string per dependency level (default: `"  "`)

**Returns:** Plain-text representation

---

### `FallacyDetector`

```python
class FallacyDetector:
```

Detect logical fallacies and structural problems in a reasoning chain.

**Checks performed:**

1. **Broken dependencies** (`BROKEN_DEPENDENCY`, error): `depends_on` contains
   a step ID not present in `chain.steps`
2. **Circular reasoning** (`CIRCULAR_REASONING`, error): dependency cycles
   detected via DFS with white/gray/black coloring
3. **Unsupported conclusions** (`UNSUPPORTED_CONCLUSION`, error): `CONCLUSION`
   step with empty `depends_on`
4. **Missing premises** (`MISSING_PREMISE`, warning): `INFERENCE` step with
   empty `depends_on`

#### `validate(chain: ReasoningChain) -> ChainValidation`

Validate a reasoning chain and return all detected issues.

**Parameters:**
- `chain` — the `ReasoningChain` to validate

**Returns:**
- `ChainValidation` with `is_valid=True` only if no error-severity issues exist

**Example:**

```python
from aumai_reasonflow.core import FallacyDetector

detector = FallacyDetector()
validation = detector.validate(chain)

if not validation.is_valid:
    for issue in validation.errors:
        print(f"[{issue.fallacy_type.value}] {issue.step_id}: {issue.message}")
```

#### `_detect_cycles(chain: ReasoningChain) -> set[str]`

*Internal.* Return the set of step IDs involved in dependency cycles.

Uses DFS white/gray/black coloring. When a back-edge to a gray ancestor is
found, all nodes on the current DFS path from that ancestor to the end of the
stack are added to the cyclic set (not just the two endpoints).

---

## Module: `aumai_reasonflow.cli`

### `main`

CLI entry point registered as `aumai-reasonflow`.

| Command | Description |
|---|---|
| `build` | Build a `ReasoningChain` from a JSON specification file |
| `validate` | Validate an existing chain JSON file for logical fallacies (exits 1 on invalid) |
| `visualize` | Render a chain as Mermaid or plain text |

See [README.md](../README.md) for full CLI usage with examples.

---

## Package-level exports

`aumai_reasonflow.__version__` — current version string (`"0.1.0"`).

Import directly from submodules:

```python
from aumai_reasonflow.core import ChainBuilder, ChainVisualizer, FallacyDetector
from aumai_reasonflow.models import (
    ReasoningChain,
    ReasoningStep,
    StepType,
    FallacyType,
    ValidationIssue,
    ChainValidation,
)
```
