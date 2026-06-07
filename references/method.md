# Convex/Concave Line-Separation Method

The source note proves tight one-variable inequalities by rewriting them as one side above another side and finding a line between them.

## Normal Form

Start with an inequality and move all terms to one side:

```text
F(x) >= 0
```

Then move positive top-level terms of `F` to the left and negative top-level terms to the right:

```text
left(x) >= right(x)
```

The supported proof goal is:

```text
min_x (left(x) - right(x)) >= 0
```

In this skill, `left` must be convex or affine and `right` must be concave or affine after the positive/negative split. The terms convex and concave are used in the English mathematical sense.

When a separating line is found, prove:

```text
left(x) >= h(x) >= right(x)
```

## Tangent Templates

For a rational positive slope parameter `q`, use tangent-line forms:

- Exponential:
  `exp(x) >= q * (x - log(q) + 1)`, tangent at `x = log(q)`.
- Logarithm:
  `log(x) <= q*x - 1 - log(q)`, tangent at `x = 1/q`.
- Power, convex case `a > 1` or `a < 0`:
  `x^a >= q*x + (1-a)/a * (q/a)^(a/(a-1))`, tangent where `a*x^(a-1)=q`.
- Power, concave case `0 < a < 1`:
  `x^a <= q*x + (1-a)*(a/q)^(a/(1-a))`, tangent where `a*x^(a-1)=q`.
- Constant and linear terms need no relaxation.

The practical search implemented here is:

1. Numerically locate the minimizer `x*` of `left-right`.
2. Compute continued-fraction convergents `x1, x2, ...` of `x*`.
3. Use the exact tangent line to the concave right side at each rational `xn`.
4. Since a concave function lies below its tangent, `h_n(x) >= right(x)` follows automatically.
5. Check whether `left(x) - h_n(x)` has nonnegative global minimum.
6. Stop at the first successful convergent and print the tangent with exact rational data.

## Source Example

For:

```text
exp(x) - 2*x - log(x) > 1/sqrt(2)
```

rewrite as:

```text
exp(x) > 2*x + log(x) + 1/sqrt(2)
```

The note gives the separating line:

```text
h(x) = 41/14 * (x - 12/161)
```

so the proof is split into:

```text
exp(x) > h(x)
h(x) > 2*x + log(x) + 1/sqrt(2)
```
