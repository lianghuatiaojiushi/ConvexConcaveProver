#!/usr/bin/env python3
"""Restricted convex/concave inequality prover.

This script intentionally avoids third-party symbolic libraries. It supports
top-level sums of constants, x, exp(x), log(x), and powers x^a.
"""

from __future__ import annotations

import argparse
import ast
import math
import re
from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable, List, Optional, Tuple


EPS = 1e-9


@dataclass(frozen=True)
class Atom:
    kind: str
    exponent: Optional[float] = None

    def label(self) -> str:
        if self.kind == "const":
            return "1"
        if self.kind == "linear":
            return "x"
        if self.kind == "exp":
            return "exp(x)"
        if self.kind == "log":
            return "log(x)"
        if self.kind == "power":
            return f"x^{self.exponent:g}"
        raise ValueError(f"unknown atom {self.kind}")

    def value(self, x: float) -> float:
        if self.kind == "const":
            return 1.0
        if self.kind == "linear":
            return x
        if self.kind == "exp":
            return math.exp(x)
        if self.kind == "log":
            return math.log(x)
        if self.kind == "power":
            return x ** float(self.exponent)
        raise ValueError(f"unknown atom {self.kind}")

    def d1(self, x: float) -> float:
        if self.kind == "const":
            return 0.0
        if self.kind == "linear":
            return 1.0
        if self.kind == "exp":
            return math.exp(x)
        if self.kind == "log":
            return 1.0 / x
        if self.kind == "power":
            a = float(self.exponent)
            return a * x ** (a - 1.0)
        raise ValueError(f"unknown atom {self.kind}")

    def d2_sign(self, coeff: float) -> int:
        """Return sign of coeff * atom'' on x>0: -1, 0, or 1."""
        if self.kind in {"const", "linear"}:
            return 0
        if self.kind == "exp":
            raw = 1.0
        elif self.kind == "log":
            raw = -1.0
        elif self.kind == "power":
            a = float(self.exponent)
            raw = a * (a - 1.0)
        else:
            raise ValueError(f"unknown atom {self.kind}")
        val = coeff * raw
        if val > EPS:
            return 1
        if val < -EPS:
            return -1
        return 0


@dataclass(frozen=True)
class Term:
    coeff: float
    atom: Atom

    def value(self, x: float) -> float:
        return self.coeff * self.atom.value(x)

    def d1(self, x: float) -> float:
        return self.coeff * self.atom.d1(x)

    def label(self) -> str:
        return f"{self.coeff:g}*{self.atom.label()}"


def normalize_expr(text: str) -> str:
    text = text.strip()
    text = text.replace("^", "**")
    text = re.sub(r"\bln\s*\(", "log(", text)
    text = re.sub(r"\be\s*\*\*\s*x\b", "exp(x)", text)
    return text


def split_inequality(text: str) -> Tuple[str, str, str]:
    text = normalize_expr(text)
    for op in (">=", "<=", ">", "<", "="):
        if op in text:
            lhs, rhs = text.split(op, 1)
            if op in ("<=", "<"):
                lhs, rhs = rhs, lhs
            return lhs.strip(), rhs.strip(), op
    return text, "0", ">="


def parse_number(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -parse_number(node.operand)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return parse_number(node.left) / parse_number(node.right)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
        return parse_number(node.left) ** parse_number(node.right)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "sqrt":
        if len(node.args) != 1:
            raise ValueError("sqrt expects one argument")
        return math.sqrt(parse_number(node.args[0]))
    raise ValueError(f"expected numeric constant, got {ast.dump(node)}")


def parse_atom(node: ast.AST) -> Atom:
    if isinstance(node, ast.Name) and node.id == "x":
        return Atom("linear")
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        name = node.func.id
        if len(node.args) != 1:
            raise ValueError(f"{name} expects one argument")
        arg = node.args[0]
        if not (isinstance(arg, ast.Name) and arg.id == "x"):
            raise ValueError(f"{name} only supports argument x")
        if name == "exp":
            return Atom("exp")
        if name == "log":
            return Atom("log")
        if name == "sqrt":
            return Atom("power", 0.5)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
        if isinstance(node.left, ast.Name) and node.left.id == "x":
            return Atom("power", parse_number(node.right))
    raise ValueError(f"unsupported atom {ast.dump(node)}")


def multiply_term(term: Term, factor: float) -> Term:
    return Term(term.coeff * factor, term.atom)


def parse_factor_term(node: ast.AST) -> Term:
    try:
        return Term(parse_number(node), Atom("const"))
    except ValueError:
        return Term(1.0, parse_atom(node))


def parse_product(node: ast.AST) -> Term:
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
        left = parse_product(node.left)
        right = parse_product(node.right)
        if left.atom.kind == "const":
            return multiply_term(right, left.coeff)
        if right.atom.kind == "const":
            return multiply_term(left, right.coeff)
        raise ValueError("products of two non-constant atoms are unsupported")
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        left = parse_product(node.left)
        denom = parse_number(node.right)
        return multiply_term(left, 1.0 / denom)
    return parse_factor_term(node)


def collect_terms(node: ast.AST, sign: float = 1.0) -> List[Term]:
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return collect_terms(node.left, sign) + collect_terms(node.right, sign)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Sub):
        return collect_terms(node.left, sign) + collect_terms(node.right, -sign)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
        try:
            factor = parse_number(node.left)
            return collect_terms(node.right, sign * factor)
        except ValueError:
            pass
        try:
            factor = parse_number(node.right)
            return collect_terms(node.left, sign * factor)
        except ValueError:
            pass
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        try:
            factor = parse_number(node.right)
            return collect_terms(node.left, sign / factor)
        except ValueError:
            pass
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return collect_terms(node.operand, -sign)
    return [multiply_term(parse_product(node), sign)]


def parse_terms(text: str) -> List[Term]:
    tree = ast.parse(normalize_expr(text), mode="eval")
    return collect_terms(tree.body)


def parse_as_f_terms(ineq: str) -> Tuple[List[Term], str]:
    lhs, rhs, op = split_inequality(ineq)
    terms = parse_terms(lhs) + [Term(-t.coeff, t.atom) for t in parse_terms(rhs)]
    return combine_terms(terms), op


def combine_terms(terms: Iterable[Term]) -> List[Term]:
    buckets = {}
    for t in terms:
        key = (t.atom.kind, t.atom.exponent)
        buckets[key] = buckets.get(key, 0.0) + t.coeff
    out = []
    for (kind, exponent), coeff in buckets.items():
        if abs(coeff) > EPS:
            out.append(Term(coeff, Atom(kind, exponent)))
    return out


def split_positive_negative(terms: Iterable[Term]) -> Tuple[List[Term], List[Term]]:
    left: List[Term] = []
    right: List[Term] = []
    for t in terms:
        if t.coeff >= 0:
            left.append(t)
        else:
            right.append(Term(-t.coeff, t.atom))
    return left, right


def evaluate(terms: Iterable[Term], x: float) -> float:
    return sum(t.value(x) for t in terms)


def derivative(terms: Iterable[Term], x: float) -> float:
    return sum(t.d1(x) for t in terms)


def curvature(terms: Iterable[Term]) -> str:
    signs = {t.atom.d2_sign(t.coeff) for t in terms}
    signs.discard(0)
    if not signs:
        return "affine"
    if signs == {1}:
        return "convex"
    if signs == {-1}:
        return "concave"
    return "mixed"


def minimize_convex(terms: List[Term], domain: Tuple[float, Optional[float]]) -> Tuple[float, float]:
    lo, hi = domain
    lo = max(lo, 1e-8)
    if hi is not None:
        dlo = derivative(terms, lo)
        dhi = derivative(terms, hi)
        if dlo >= 0:
            return lo, evaluate(terms, lo)
        if dhi <= 0:
            return hi, evaluate(terms, hi)
        a, b = lo, hi
    else:
        dlo = derivative(terms, lo)
        if dlo >= 0:
            return lo, evaluate(terms, lo)
        a, b = lo, 1.0
        while derivative(terms, b) <= 0 and b < 1e8:
            b *= 2.0
        if b >= 1e8 and derivative(terms, b) <= 0:
            return b, evaluate(terms, b)
    for _ in range(160):
        mid = (a + b) / 2.0
        if derivative(terms, mid) <= 0:
            a = mid
        else:
            b = mid
    x = (a + b) / 2.0
    return x, evaluate(terms, x)


def line_gap_terms(base_terms: List[Term], m: float, b: float, sign: int) -> List[Term]:
    # sign=1 gives h-base; sign=-1 gives base-h.
    line = [Term(m, Atom("linear")), Term(b, Atom("const"))]
    if sign == 1:
        return combine_terms(line + [Term(-t.coeff, t.atom) for t in base_terms])
    return combine_terms(base_terms + [Term(-m, Atom("linear")), Term(-b, Atom("const"))])


def fraction_label(frac: Fraction) -> str:
    if frac.denominator == 1:
        return str(frac.numerator)
    return f"{frac.numerator}/{frac.denominator}"


def signed_fraction_label(frac: Fraction) -> str:
    if frac == 0:
        return ""
    sign = "+" if frac > 0 else "-"
    mag = abs(frac)
    return f" {sign} {fraction_label(mag)}"


def exp_math_label(arg: str) -> str:
    if arg == "x":
        return "e^x"
    return f"e^({arg})"


def continued_fraction_convergents(x: float, max_terms: int = 12, max_denominator: int = 10000) -> List[Fraction]:
    terms: List[int] = []
    y = x
    for _ in range(max_terms):
        a = math.floor(y)
        terms.append(a)
        frac_part = y - a
        if abs(frac_part) < 1e-14:
            break
        y = 1.0 / frac_part

    convergents: List[Fraction] = []
    for i in range(1, len(terms) + 1):
        value = Fraction(terms[i - 1], 1)
        for a in reversed(terms[: i - 1]):
            value = a + Fraction(1, value)
        if value.denominator <= max_denominator and value not in convergents:
            convergents.append(value)
    return convergents


def tangent_line_at(left: List[Term], x0: float) -> Tuple[float, float]:
    m = derivative(left, x0)
    b = evaluate(left, x0) - m * x0
    return m, b


def term_tangent_expr(term: Term, point: Fraction) -> str:
    c = Fraction(term.coeff).limit_denominator(1000000)
    r = fraction_label(point)
    prefix = "" if c == 1 else "-" if c == -1 else f"{fraction_label(c)}*"
    if term.atom.kind == "const":
        return fraction_label(c)
    if term.atom.kind == "linear":
        return f"{prefix}x"
    if term.atom.kind == "exp":
        shift = signed_fraction_label(1 - point)
        return f"{prefix}{exp_math_label(r)}(x{shift})"
    if term.atom.kind == "power":
        a = term.atom.exponent
        return f"{prefix}(({r})^{a:g} + {a:g}*({r})^({a:g}-1)*(x - {r}))"
    raise ValueError(f"cannot format tangent for {term.atom.label()}")


def tangent_expr(left: List[Term], point: Fraction) -> str:
    pieces = [term_tangent_expr(t, point) for t in left]
    return " + ".join(pieces).replace("+ -", "- ")


def find_line(left: List[Term], right: List[Term], domain: Tuple[float, Optional[float]], x_center: float) -> Optional[dict]:
    # Tangent to convex left side. It is automatically below left.
    candidates = continued_fraction_convergents(x_center)
    attempts = []
    for index, rational in enumerate(candidates, start=1):
        x0 = float(rational)
        if x0 <= domain[0] or (domain[1] is not None and x0 >= domain[1]):
            continue
        m, b = tangent_line_at(left, x0)
        lower_gap = line_gap_terms(right, m, b, 1)  # h - right
        x_gap, min_gap = minimize_convex(lower_gap, domain)
        attempts.append((index, rational, min_gap))
        if min_gap >= -1e-7:
            return {
                "convergent_index": index,
                "rational": rational,
                "x0": x0,
                "m": m,
                "b": b,
                "expr": tangent_expr(left, rational),
                "right_gap_min_x": x_gap,
                "right_gap_min": min_gap,
                "attempts": attempts,
            }
    return None


def parse_domain(text: str) -> Tuple[float, Optional[float]]:
    if not text:
        return (1e-8, None)
    parts = [p.strip() for p in text.split(",")]
    if len(parts) != 2:
        raise ValueError("domain must look like '0,inf' or '0,10'")
    lo = float(parts[0])
    hi = None if parts[1].lower() in {"inf", "infinity", "+inf"} else float(parts[1])
    return (lo, hi)


def fmt_terms(terms: List[Term]) -> str:
    if not terms:
        return "0"
    return " + ".join(t.label() for t in terms)


def fmt_coeff_abs(coeff: Fraction) -> str:
    if coeff.denominator == 1:
        return str(coeff.numerator)
    return f"{coeff.numerator}/{coeff.denominator}"


def fmt_atom_natural(atom: Atom) -> str:
    if atom.kind == "const":
        return ""
    if atom.kind == "linear":
        return "x"
    if atom.kind == "exp":
        return exp_math_label("x")
    if atom.kind == "log":
        return "ln x"
    if atom.kind == "power":
        if abs(float(atom.exponent) - 0.5) < 1e-12:
            return "√x"
        return f"x^{float(atom.exponent):g}"
    raise ValueError(f"unknown atom {atom.kind}")


def fmt_natural_terms(terms: List[Term]) -> str:
    pieces = []
    for t in terms:
        coeff = Fraction(t.coeff).limit_denominator(1000000)
        if coeff == 0:
            continue
        sign = "-" if coeff < 0 else "+"
        mag = abs(coeff)
        atom = fmt_atom_natural(t.atom)
        if t.atom.kind == "const":
            body = fmt_coeff_abs(mag)
        elif mag == 1:
            body = atom
        else:
            body = f"{fmt_coeff_abs(mag)}*{atom}"
        pieces.append((sign, body))
    if not pieces:
        return "0"
    first_sign, first_body = pieces[0]
    out = first_body if first_sign == "+" else f"-{first_body}"
    for sign, body in pieces[1:]:
        out += f" {sign} {body}"
    return out


def affine_line_from_expr(text: str) -> Tuple[float, float]:
    terms = combine_terms(parse_terms(text))
    m = 0.0
    b = 0.0
    for t in terms:
        if t.atom.kind == "linear":
            m += t.coeff
        elif t.atom.kind == "const":
            b += t.coeff
        else:
            raise ValueError("--line must be an affine expression in x")
    return m, b


def verify_line(left: List[Term], right: List[Term], domain: Tuple[float, Optional[float]], m: float, b: float) -> dict:
    left_gap = line_gap_terms(left, m, b, -1)  # left - h
    right_gap = line_gap_terms(right, m, b, 1)  # h - right
    x_left, min_left = minimize_convex(left_gap, domain)
    x_right, min_right = minimize_convex(right_gap, domain)
    return {
        "m": m,
        "b": b,
        "left_gap_min_x": x_left,
        "left_gap_min": min_left,
        "right_gap_min_x": x_right,
        "right_gap_min": min_right,
        "ok": min_left >= -1e-8 and min_right >= -1e-8,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Restricted convex/concave inequality prover")
    parser.add_argument("inequality", help="Example: exp(x)-2*x-log(x)-1/sqrt(2)>=0")
    parser.add_argument("--domain", default="0,inf", help="positive domain, e.g. 0,inf or 0,10")
    parser.add_argument("--line", help="optional affine proof line to verify, e.g. '41/14*(x-12/161)'")
    parser.add_argument("--no-line", action="store_true", help="skip line-proof search")
    args = parser.parse_args()

    domain = parse_domain(args.domain)
    f_terms, op = parse_as_f_terms(args.inequality)
    left, right = split_positive_negative(f_terms)
    diff = combine_terms(left + [Term(-t.coeff, t.atom) for t in right])
    left_curv = curvature(left)
    right_curv = curvature(right)
    diff_curv = curvature(diff)

    print("normalized:")
    print(f"  left  = {fmt_terms(left)}")
    print(f"  right = {fmt_terms(right)}")
    print(f"  F     = left - right = {fmt_terms(diff)}")
    print("curvature:")
    print(f"  left: {left_curv}")
    print(f"  right: {right_curv}")
    print(f"  F: {diff_curv}")

    template_ok = left_curv in {"convex", "affine"} and right_curv in {"concave", "affine"}
    if not template_ok:
        print("result: inconclusive")
        print("reason: after moving positive terms left and negative terms right, left is not convex/affine or right is not concave/affine")
        return 2

    if diff_curv not in {"convex", "affine"}:
        print("result: inconclusive")
        print("reason: left-right is not recognized as convex/affine by the restricted rules")
        return 2

    x_min, f_min = minimize_convex(diff, domain)
    strict = op in {">", "<"}
    ok = f_min > 1e-8 if strict else f_min >= -1e-8
    print("minimum:")
    print(f"  x ~= {x_min:.12g}")
    print(f"  min(left-right) ~= {f_min:.12g}")
    print(f"result: {'proved' if ok else 'failed'}")

    if ok and args.line:
        m, b = affine_line_from_expr(args.line)
        checked = verify_line(left, right, domain, m, b)
        print("provided_line:")
        print(f"  h(x) = ({checked['m']:.12g})*x + ({checked['b']:.12g})")
        print(f"  min(left-h) ~= {checked['left_gap_min']:.12g} at x ~= {checked['left_gap_min_x']:.12g}")
        print(f"  min(h-right) ~= {checked['right_gap_min']:.12g} at x ~= {checked['right_gap_min_x']:.12g}")
        print(f"  proof_line: {'valid' if checked['ok'] else 'invalid'}")

    if ok and not args.no_line and left_curv == "convex" and right_curv in {"concave", "affine"}:
        cert = find_line(left, right, domain, x_min)
        if cert:
            print("line_proof:")
            print(f"  convergent_index = {cert['convergent_index']}")
            print(f"  tangent_at = {fraction_label(cert['rational'])} ~= {cert['x0']:.12g}")
            print(f"  exact: h(x) = {cert['expr']}")
            print(f"  h(x) = ({cert['m']:.12g})*x + ({cert['b']:.12g})")
            print(f"  min(h-right) ~= {cert['right_gap_min']:.12g} at x ~= {cert['right_gap_min_x']:.12g}")
            print("  left-h >= 0 follows from convexity of left and tangent construction")
            relation = ">" if strict and cert["right_gap_min"] > 1e-8 else ">="
            print("proof:")
            print("  注意到")
            print(f"  {fmt_natural_terms(left)}>={cert['expr']}{relation}{fmt_natural_terms(right)}")
            print("  证毕！")
        else:
            print("line_proof: not found by the built-in finite candidate search")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
