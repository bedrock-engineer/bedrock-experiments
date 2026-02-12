import marimo

__generated_with = "0.19.7"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    return


@app.cell
def _(np, pl, pv):
    chnl_img_data = pv.examples.load_channels()
    # Merge facies 1 & 2 and 3 & 4
    facies = chnl_img_data["facies"]
    facies[np.isin(facies, [1, 2])] = 2
    facies[np.isin(facies, [3, 4])] = 3
    facies[facies == 0] = 1
    facies = pl.Series("facies", chnl_img_data["facies"]).unique()
    chnl_img_data
    return


if __name__ == "__main__":
    app.run()
