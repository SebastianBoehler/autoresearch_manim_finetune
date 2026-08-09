# Model Benchmark Findings, 2026-04-26

## Decision

Use `xiaomi/mimo-v2-pro` as the default API model for Manim generation workflows.

The 21-case public Manim benchmark is the strongest same-split API comparison currently available in this repo. Xiaomi MiMo-V2-Pro is the quality leader there:

| Model | Cases | Score | Render | Syntax |
| --- | ---: | ---: | ---: | ---: |
| Xiaomi MiMo-V2-Pro | 21 | 0.791 | 87.5% | 81.0% |
| Xiaomi MiMo-V2-Pro + Hermes skill | 21 | 0.717 | 80.0% | 76.2% |
| MiniMax M2.7 | 21 | 0.658 | 53.3% | 76.2% |
| Qwen 2.5 Coder 3B LoRA | 21 | 0.656 | 56.2% | 76.2% |
| Qwen 2.5 Coder 3B base | 21 | 0.585 | 25.0% | 81.0% |

Source: `artifacts/benchmarks/model-benchmark-report.json`

## Fine-Tune Read

The local Qwen 2.5 Coder 3B LoRA is a real improvement over the base model:

| Comparison | Score Delta | Render Delta | Syntax Delta |
| --- | ---: | ---: | ---: |
| LoRA vs base | +0.071 (+12.1%) | +31.2 pp | -4.8 pp |

The promoted local Manim stack reaches `0.709` score and `72.2%` render on the newer 22-case gold-silver split, but that split is not directly comparable to the 21-case public API leaderboard.

## API Caveat

The fresh 6-case OpenRouter smoke run favored GPT-5.4-mini:

| Model | Cases | Score | Render | Syntax |
| --- | ---: | ---: | ---: | ---: |
| GPT-5.4-mini | 6 | 0.969 | 100.0% | 100.0% |
| Xiaomi MiMo-V2-Pro | 6 | 0.654 | 50.0% | 66.7% |

Source: `artifacts/benchmarks/openrouter-manim-xiaomi-gptmini-smoke/leaderboard.json`

Treat this as a warning that GPT-5.4-mini deserves a full 21-case Manim run. Until that exists, Xiaomi remains the safer default because it won the complete public split.

## Local Model Cleanup

The Bonsai/Ternary Bonsai MLX family is not a near-term Manim default. Existing local taste checks showed weak render behavior compared with the Qwen LoRA path, and the same family failed zero-shot Remotion compile/render checks. The HF cache copies were removed to save disk space.

Kept local models:

- `Qwen/Qwen2.5-Coder-3B-Instruct`
- `mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit`
- `mlx-community/Qwen2.5-Coder-0.5B-Instruct-4bit`

Removed cache models:

- `prism-ml/Bonsai-8B-mlx-1bit`
- `prism-ml/Ternary-Bonsai-1.7B-mlx-2bit`
- `prism-ml/Ternary-Bonsai-4B-mlx-2bit`
- `prism-ml/Ternary-Bonsai-8B-mlx-2bit`
- `mlx-community/Qwen2.5-3B-Instruct-4bit`
