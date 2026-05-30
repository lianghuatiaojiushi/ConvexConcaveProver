# 凹凸不等式证明器ConvexConcaveProver

凹凸不等式证明器`ConvexConcaveProver` 是一个用于证明单变量不等式的小型证明器。它面向一类特定的不等式证明方法：把问题整理成凸函数大于凹函数，然后在二者之间寻找一条直线作为中间函数。

核心目标是找到：

$$
\operatorname{left}(x) \ge h(x) \ge \operatorname{right}(x)
$$

一旦找到这样的直线 $h(x)$，原不等式就被证明。

## 证明方法

给定一个不等式，证明器会按以下流程处理：

1. 先把不等式整理成 $F(x)\ge 0$。
2. 将 $F(x)$ 中的正项移动到左边，负项取正后移动到右边。
3. 检查 $\operatorname{left}(x)$ 是否为 $\text{convex}$ 或 $\text{affine}$，$\operatorname{right}(x)$ 是否为 $\text{concave}$ 或 $\text{affine}$。
4. 数值寻找 $\operatorname{left}(x)-\operatorname{right}(x)$ 的全局最小点 $x^\ast$。
5. 对 $x^\ast$ 做连分数展开，依次取收敛分数 $x_1,x_2,\ldots$ 作为候选切点。
6. 在候选切点 $x_n$ 处作 $\operatorname{left}(x)$ 的切线 $h_n(x)$。
7. 检查 $h_n(x)-\operatorname{right}(x)$ 的全局最小值是否非负。
8. 若成功，则输出一条形式更美观的证明。

数值计算只用于寻找候选切点；最终展示给用户的证明会尽量使用有理数切点和数学表达式，例如：

$$
e^{1/2}\left(x+\frac12\right)
$$

## 支持的表达式

目前支持以下函数和表达式：

- 指数函数 $e^x$
- 对数函数 $\ln x$
- 幂函数`x^a` 或 `x**a`，其中 $a$ 是数字
- $x$
- 常数

支持的整体形式是这些基本项的顶层加减和常数倍，例如：

$$
e^x-x-\sqrt{x}-\frac{211}{481}>0
$$

$$
e^x-\ln x-\frac{261}{112}>0
$$

暂时不支持任意嵌套函数、非线性项乘积、三角函数或多变量不等式。

## 使用方法

在项目根目录运行：

```bash
python scripts/prove.py "exp(x) - x - sqrt(x) - 211/481 > 0"
```

示例输出：

```text
normalized:
  left  = 1*exp(x)
  right = 1*x + 1*x^0.5 + 0.438669*1
curvature:
  left: convex
  right: concave
  F: convex
minimum:
  x ~= 0.524832477571
  min(left-right) ~= 0.00222053945774
result: proved
line_proof:
  tangent_at = 1/2 ~= 0.5
  exact: h(x) = e^(1/2)(x + 1/2)
proof:
  注意到
  e^x>=e^(1/2)(x + 1/2)>x + √x + 211/481
  证毕！
```

也可以验证手动给出的直线：

```bash
python scripts/prove.py "exp(x) - 2*x - log(x) - 1/sqrt(2) >= 0" --line "41/14*(x-12/161)"
```

## 示例

证明：

$$
e^x-\ln x>\frac{261}{112}
$$

运行：

```bash
python scripts/prove.py "exp(x) - log(x) - 261/112 > 0"
```

证明器会找到切点：

$$
x_0=\frac{17}{30}
$$

对应切线：

$$
h(x)=e^{17/30}\left(x+\frac{13}{30}\right)
$$

并给出结论：

注意到

$$
e^x\ge e^{17/30}\left(x+\frac{13}{30}\right)>\ln x+\frac{261}{112}
$$

证毕！
