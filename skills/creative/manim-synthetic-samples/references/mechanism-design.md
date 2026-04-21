# Mechanism Design For Manim Samples

## Research Translation

The Simula pattern treats synthetic data generation as a controllable mechanism, not a prompt lottery. For this repo, translate the idea into four controls:

1. Global diversification: cover the Manim concept space with an explicit taxonomy.
2. Local diversification: create distinct prompt/code instantiations inside the same node set.
3. Complexification: raise difficulty independently from topic coverage.
4. Quality checks: use critics, static validation, render validation, and human review.

The goal is not maximum novelty per sample. The goal is a dataset whose coverage, complexity, and failure modes are explainable.

## Coverage Axes

Use these axes when planning a candidate batch:

| Axis | Example nodes | Why it matters |
|---|---|---|
| Manim API feature | `Axes`, `NumberPlane`, `BarChart`, `ValueTracker`, `always_redraw`, `Surface`, `ZoomedScene` | Forces useful API breadth. |
| Animation mechanic | transform, reveal, tracking, camera move, comparison, staged cleanup | Trains temporal structure, not just static drawing. |
| Visual layout | centered diagram, split comparison, fixed overlay, table plus graph, 3D plus annotation | Reduces layout mode collapse. |
| Knowledge domain | math, physics, ML, chemistry, economics, CS, neuroscience | Keeps prompts semantically varied. |
| Duration | 5s, 10s, 20s, 30s | Controls pacing and code length. |
| Scene class | `Scene`, `ThreeDScene`, `MovingCameraScene`, `ZoomedScene` | Covers different Manim execution models. |
| Render risk | low, medium, high | Helps allocate review effort. |

## Batch Design Template

Before creating records, write a short plan:

```markdown
Batch goal: [one sentence]
Target size: [N]
Complexification fraction: [0.2-0.4]
Canonical gaps observed:
- [gap 1 with evidence]
- [gap 2 with evidence]

Sampling strategies:
1. [strategy name]: [compatible axes], target count [n]
2. [strategy name]: [compatible axes], target count [n]

Reject upfront:
- [illogical or unwanted combination]
- [known fragile construct unless explicitly targeted]
```

## Meta-Prompt Recipe

A strong sample prompt contains:

- Duration: "Create a 12-second Manim scene..."
- Topic: the concept being taught.
- Visual objects: concrete shapes, axes, surfaces, labels, panels, or paths.
- Motion: what changes over time.
- Readability constraint: what must remain clear.
- Completion target: one scene, no external assets, plain Manim unless requested.

Weak:

```text
Create an animation about gradient descent.
```

Strong:

```text
Create a 20-second Manim scene that compares a steep and gentle gradient descent path on one contour map. Show two colored paths, moving probe dots, a fixed legend, and a final caption that explains why step size changes convergence behavior.
```

## Local Diversity Checks

For any pair of candidates in the same topic family, require at least two meaningful differences:

- Different primary Manim construct.
- Different layout.
- Different motion mechanic.
- Different domain framing.
- Different duration tier.
- Different target base scene class.

Reject variants that only rename labels or change colors.

## Complexification Moves

Use these only when the batch plan calls for complex examples:

- Add `ValueTracker` plus `always_redraw` for dynamic state.
- Add fixed overlays to 3D scenes with `add_fixed_in_frame_mobjects`.
- Add a zoom or moving camera to reveal a local detail.
- Compare two strategies or states in one scene.
- Add staged captions that change with the visual state.

Do not complexify by adding unrelated objects. Complexity must make the teaching target richer.

## Quality Critic Questions

Ask these before staging a candidate:

1. Does the prompt describe a visible story that the code actually implements?
2. Are all `must_contain` snippets semantically central, not decorative?
3. Are all labels readable and unlikely to overlap?
4. Does the code use only plain Manim unless custom libraries are explicit?
5. Is the scene likely to render inside the target duration and timeout?
6. Does this record add coverage compared with the existing dataset?
7. Would training on this sample teach a reusable Manim pattern?

If any answer is no, revise or reject the candidate.
