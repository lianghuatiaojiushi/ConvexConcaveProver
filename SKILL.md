---
name: ConvexConcaveProver
description: Prove one-variable inequalities by separating positive terms to the left and negative terms to the right, then verifying a convex/concave tangent-line proof for expressions built from exp(x), log(x), powers x^a, constants, and linear terms. Use when Codex needs to prove or check inequalities of this restricted convex-concave form, find a line between the two sides, or reproduce the proof method from the supplied Chinese inequality note.
---

# Convex-Concave Prover

Use this skill to prove restricted one-variable inequalities with the method:

1. Rewrite the inequality as `F(x) >= 0`.
2. Move positive top-level terms of `F` to the left and negative top-level terms to the right.
3. Check the left side is convex or affine and the right side is concave or affine.
4. Minimize `left(x) - right(x)` on the positive domain.
5. When possible, use continued-fraction convergents of the numeric minimizer to choose rational points, construct tangent lines to the concave right side, and report an exact-looking line proof.

## Supported Input

Use `scripts/prove.py` for deterministic checks.

Supported atoms:

- `exp(x)` or `e^x`
- `log(x)`, `ln(x)`
- `x^a` or `x**a`, where `a` is numeric; `sqrt(x)` is accepted as `x^0.5`
- `x`
- constants, including `sqrt(c)`

Supported top-level operations are sums/differences of constant multiples of supported atoms. Products such as `2*x`, `(3/5)*log(x)`, and `-1/sqrt(2)` are allowed.

## Workflow

Run:

```bash
python scripts/prove.py "exp(x) - 2*x - log(x) - 1/sqrt(2) >= 0"
```

To verify a proposed line from a hand proof:

```bash
python scripts/prove.py "exp(x) - 2*x - log(x) - 1/sqrt(2) >= 0" --line "41/14*(x-12/161)"
```

If the system Python is unavailable in the Codex desktop workspace, use the bundled Python runtime exposed by `load_workspace_dependencies`.

Interpretation:

- `left` contains the positive terms.
- `right` contains the magnitudes of the negative terms.
- `F = left - right`.
- A successful result requires `left` to be convex/affine, `right` to be concave/affine, and `min F >= 0` on the selected domain.
- A line proof additionally requires `left(x) >= h(x) >= right(x)` on the domain. Construct `h` as the tangent to the concave right side, so `h >= right` follows automatically. Then verify `left - h >= 0`. Candidate tangent points are tried as rational continued-fraction convergents of the numeric minimizer.
- When a line proof succeeds, end user-facing proofs with `注意到`, the formula, and `证毕！` each on its own line:

```text
注意到
左边表达式>(或>=)h(x)>(或>=)右边表达式
证毕！
```

Replace both ends with the actual normalized expressions, not placeholders like `f(x)` or `g(x)`. Choose `>` or `>=` according to the checked inequality and whether the proof is strict.

Read [references/method.md](references/method.md) when you need the proof template or the tangent-line formulas from the source note.

## Important Limits

Treat the script as a proof assistant for this narrow method, not a general CAS. It does not solve arbitrary expressions, products of nonlinear functions, nested functions, multi-variable inequalities, or inequalities outside the positive-domain assumptions needed by `log(x)` and non-integer powers. Here "convex/concave" is used in the English mathematical sense: the supported default template is convex-left greater than concave-right.
