import marimo

__generated_with = "0.25.0"
app = marimo.App()


@app.cell
def _():
    import marimo as mo

    mode = mo.app_meta().mode
    print("mo.app_meta().mode =", mode)
    return (mode,)


if __name__ == "__main__":
    app.run()
