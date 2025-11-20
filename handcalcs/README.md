# `mocalc`

A Python package for creating interactive mathematical calculations in a notebook environment.

- Variables can be defined and reused in calculations.
  - value
  - units
  - description
  - latex symbol
  - example values
  - max
  - min
- Formulas are functions that operate on these variables.
- Units are handled using Pint.
- The functions return the result as well as a detailed calculation breakdown using LaTeX rendering.

Basically it should be like handcalcs but with more structure around defining variables and formulas and like CalcPad but in Python.

```python
def formula(x: Variable, y: Variable) -> Variable:
    return x + y
```

## Inspiration

- SymPy
- CalcPad
- handcalcs
- DesignCheck

## Extras

### Nice SymPy example from StackOverflow

```python
from pint.pint_eval import build_eval_tree, tokenizer
from pint.util import string_preprocessor
from sympy.parsing.sympy_parser import parse_expr
from sympy import Symbol, solve

# define system of equations (Note: 0 = 1 m - A instead of A = 1 m)
equations = [
    "1 m - A",
    "A + 200 mm - B",
    "B * kg/m - C",
    "A * B * C - D"
]

# define unknowns
unknowns = ["A", "B", "C", "D"]

# parse equations
# note: parsing first with pint to convert 200 mm -> 200 * mm etc.
parsed = [
  parse_expr(build_eval_tree(tokenizer(string_preprocessor(eq))).to_string())
  for eq in equations
]

# solve equation system
solution = solve(parsed, [Symbol(s) for s in unknowns])

# parse units in solution
solution = [ureg(str(r)).to_base_units() for r in solution[0]]

# for reference
expected = [
    ureg("1 m"),  # A
    ureg("1.2 m"),  # B
    ureg("1.2 kg"),  # C
    ureg("1.44 kg * m^2"),  # D
]
solution
```
