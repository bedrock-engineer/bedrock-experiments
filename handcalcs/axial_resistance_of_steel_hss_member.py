import marimo

__generated_with = "0.17.7"
app = marimo.App(width="medium")


@app.cell
def _():
    from dataclasses import dataclass
    from typing import Optional

    import marimo as mo
    import pint
    import sympy
    import sympy as sp

    ureg = pint.UnitRegistry(auto_reduce_dimensions=True)
    ureg.formatter.default_format = "~L"
    Q_ = ureg.Quantity
    return Optional, Q_, dataclass, mo, pint, sp, sympy, ureg


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Axial Resistance of Steel HSS Member

    As per CSA S16-17
    """)
    return


@app.cell(hide_code=True)
def _(
    beam_length,
    c_f,
    cross_sectional_area,
    effective_length_factor,
    elastic_modulus,
    mo,
    radius_gyration,
    strength_reduction_factor,
    yield_strength,
):
    mo.md(rf"""
    |     |     |     |     |
    |--------------|--------|---|-------|
    | **Loads** |  |  |  |
    | {c_f.name} | ${c_f.latex_symbol}$ | = | ${c_f.quantity}$ |
    | **Member geometry** |  |  |  |
    | {beam_length.name} | ${beam_length.latex_symbol}$ | = | ${beam_length.quantity}$ |
    | {effective_length_factor.name} | ${effective_length_factor.latex_symbol}$ | = | ${effective_length_factor.quantity}$ |
    | **Material properties** |  |  |  |
    | {elastic_modulus.name} | ${elastic_modulus.latex_symbol}$ | = | ${elastic_modulus.quantity}$ |
    | {yield_strength.name} | ${yield_strength.latex_symbol}$ | = | ${yield_strength.quantity}$ |
    | {strength_reduction_factor.name} | ${strength_reduction_factor.latex_symbol}$ | = | ${strength_reduction_factor.quantity}$ |
    | **Member section properties** |  |  |  |
    | {cross_sectional_area.name} | ${cross_sectional_area.latex_symbol}$ | = | ${cross_sectional_area.quantity}$ |
    | {radius_gyration.name} | ${radius_gyration.latex_symbol}$ | = | ${radius_gyration.quantity}$ |
    """)
    return


@app.cell
def _(Q_, mo, render_subs_evalf, sp):
    F_e, k, E, L, r_y = sp.symbols("F_e k E L r_y")

    euler_buckling_expr = (sp.pi**2 * E) / ((k * L / r_y) ** 2)

    inputs = {
        k: Q_(1, ""),
        E: Q_(200, "GPa"),
        L: Q_(6.5, "m"),
        r_y: Q_(76.1, "mm"),
    }

    buckling_stress, handcalc_latex = render_subs_evalf(
        expr=euler_buckling_expr,
        inputs=inputs,
        output_symbol=F_e,
        output_unit="GPa",
        output_n_decimals=3
    )

    mo.md(handcalc_latex)
    return


@app.cell
def _(Variable):
    # Loads
    c_f = Variable(
        name="Compressive force", latex_symbol="C_f", unit="kN", value=275
    )

    # Member geometry
    beam_length = Variable(
        name="Beam length", latex_symbol="L", unit="m", value=6.5
    )
    effective_length_factor = Variable(
        name="Effective length factor", latex_symbol="k", value=1
    )

    # Material properties
    strength_reduction_factor = Variable(
        name="Strength reduction factor", latex_symbol=r"\phi_s", value=0.85
    )
    elastic_modulus = Variable(
        name="Elastic modulus", latex_symbol="E", unit="GPa", value=200
    )
    yield_strength = Variable(
        name="Yield strength", latex_symbol="F_y", unit="MPa", value=400
    )
    n = Variable(name="Strain-hardening exponent", latex_symbol="n", value=1.34)

    # Member section properties
    cross_sectional_area = Variable(
        name="Cross-sectional area", latex_symbol="A", unit="mm^2", value=10_300
    )
    radius_gyration = Variable(
        name="Radius of gyration about the y-axis",
        latex_symbol="r_y",
        unit="mm",
        value=76.1,
    )
    return (
        beam_length,
        c_f,
        cross_sectional_area,
        effective_length_factor,
        elastic_modulus,
        radius_gyration,
        strength_reduction_factor,
        yield_strength,
    )


@app.cell
def _(Optional, pint, pint_to_sympy_base_unit_quantity, sympy, ureg):
    from sympy import latex


    def render_subs_evalf(
        expr: sympy.Expr,
        inputs: dict[sympy.Symbol : pint.Quantity],
        output_symbol: sympy.Symbol,
        output_unit: Optional[str] = None,
        output_n_decimals: Optional[int] = None,
    ):
        # Generate LaTeX expression with substituted quantities
        # TODO: Prevent that stuff gets replaced that shouldn't,
        # this can now happen when the latex(symbol) occurs multiple times.
        # Possible solution: first substitude with ridiculous stuff, then replace.
        substituted_latex = latex(expr)
        for symbol, quantity in inputs.items():
            substituted_latex = substituted_latex.replace(
                latex(symbol), rf"\medspace{quantity:~L}"
            )

        # Evaluate expression
        base_unit_inputs = {
            k: pint_to_sympy_base_unit_quantity(v) for k, v in inputs.items()
        }
        substituted = expr.subs(base_unit_inputs).evalf()
        output_quantity = ureg(f"{substituted}")
        if output_unit:
            output_quantity = output_quantity.to(output_unit)

        # Nicely format the output
        decimal_fmt = ""
        if output_n_decimals is not None:
            decimal_fmt = f".{output_n_decimals}f"
        output_latex = f"{output_quantity:{decimal_fmt}~L}"

        # Create the LaTeX handcalc
        align = "{align*}"
        handcalc_latex = rf"""
        $$
        \begin{align}
        {latex(output_symbol)} &= {latex(expr)} \\
        &= {substituted_latex} \\
        {latex(output_symbol)} &= {output_latex}
        \end{align}
        $$
        """
        return output_quantity, handcalc_latex
    return (render_subs_evalf,)


@app.cell
def _(pint, sympy):
    def pint_to_sympy_base_unit_quantity(
        pint_quantity: pint.Quantity,
    ) -> sympy.Expr:
        # Return quantity magnitude if dimensionless
        if pint_quantity.dimensionality == {}:
            return pint_quantity.magnitude
    
        base_unit_quantity = pint_quantity.to_base_units()
        magnitude = base_unit_quantity.magnitude
        base_units = base_unit_quantity.units
        # Convert the pint base units string with compact default formatting (~D) to sympy.Expr
        sympy_base_units = sympy.sympify(f"{base_unit_quantity.units:~D}")
        return magnitude * sympy_base_units
    return (pint_to_sympy_base_unit_quantity,)


@app.cell
def _(Optional, dataclass, ureg):
    @dataclass
    class Variable:
        """
        A variable with a descriptive name, LaTeX symbol and unit of measurement.

        Attributes:
            name: Variable descriptive name
            latex_symbol: LaTeX representation
            unit: Unit string (e.g., 'm', 'kg', 'm/s^2')
            value: Numerical value
        """

        name: str
        latex_symbol: str
        value: float
        unit: Optional[str] = None

        def __post_init__(self):
            """Validate and create Pint Quantity if units specified."""
            if self.unit:
                self.quantity = ureg.Quantity(self.value, self.unit)
            else:
                self.quantity = ureg.Quantity(self.value, "")
        
            self.si_value = self.quantity.to_base_units().magnitude

        def _repr_markdown_(self) -> str:
            """Markdown representation."""
            return rf"{self.name}: $\quad {self.latex_symbol} = {self.quantity:~L}$"
    
        def __str__(self) -> str:
            return self._repr_markdown_()
    return (Variable,)


if __name__ == "__main__":
    app.run()
