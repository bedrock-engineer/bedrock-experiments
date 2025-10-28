import marimo

__generated_with = "0.17.2"
app = marimo.App(width="medium")


@app.cell
def _():
    from pathlib import Path

    import marimo as mo
    import numpy as np
    import polars as pl
    import pyvista as pv
    from matplotlib import colormaps
    from matplotlib.colors import ListedColormap

    return ListedColormap, Path, colormaps, mo, np, pl, pv


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
    return chnl_img_data, facies


@app.cell
def _(chnl_img_data, np):
    chnl_unstructured_grid = chnl_img_data.cast_to_unstructured_grid()
    # Ghost all
    ghosts = np.argwhere(chnl_unstructured_grid["facies"] == 1)
    # This will act on the mesh inplace to mark those cell indices as ghosts
    chnl_unstructured_grid.remove_cells(ghosts, inplace=True)
    chnl_unstructured_grid
    return (chnl_unstructured_grid,)


@app.cell
def _(mo):
    plot_img_data = mo.ui.run_button(label="Press to plot all data")
    plot_unstructured_grid = mo.ui.run_button(label="Press to plot ghosted data")
    mo.hstack([plot_img_data, plot_unstructured_grid], justify="space-around")
    return plot_img_data, plot_unstructured_grid


@app.cell
def _(
    ListedColormap,
    chnl_img_data,
    chnl_unstructured_grid,
    colormaps,
    facies,
    np,
    plot_img_data,
    plot_unstructured_grid,
):
    # Limit categorical and continuous colormaps to 5 colors
    n_facies = facies.len()
    cat_rgb = (np.array(colormaps["tab10"].colors[:n_facies]) * 255).astype(int)[:, :3]
    cont_rgb = (colormaps["viridis"](np.linspace(0, 1, n_facies))[:, :3] * 255).astype(
        int
    )

    if plot_img_data.value:
        chnl_img_data.plot(cmap=ListedColormap(cont_rgb / 255))
    elif plot_unstructured_grid.value:
        chnl_unstructured_grid.plot(
            cmap=ListedColormap(cont_rgb / 255), clim=[facies.min(), facies.max()]
        )
    return (cont_rgb,)


@app.cell
def _(cont_rgb):
    facies_map = {
        1: {"label": "Flood Plane", "rgb": cont_rgb[0]},
        2: {"label": "Sand", "rgb": cont_rgb[1]},
        3: {"label": "Silt", "rgb": cont_rgb[2]},
    }
    facies_map
    return (facies_map,)


@app.cell
def _(chnl_img_data, extract_threshold_surface_meshes, facies_map, mo):
    threshold_meshes = extract_threshold_surface_meshes(
        chnl_img_data,
        "facies",
        facies_map,
        mo.notebook_location().parent / "data" / "threshold_meshes",
    )
    return


@app.cell
def _(chnl_img_data, extract_ghosted_surface_meshes, facies_map, mo):
    ghosted_meshes = extract_ghosted_surface_meshes(
        chnl_img_data,
        "facies",
        facies_map,
        mo.notebook_location().parent / "data" / "ghosted_meshes",
    )
    return


@app.cell
def _(Path, np):
    def extract_threshold_surface_meshes(
        pv_volumetric_mesh,
        category_name: str,
        category_map: dict,
        save_path: Path | None = None,
    ) -> dict:
        surface_meshes = {}
        for cat_int, v in category_map.items():
            cat_int = int(cat_int)
            # Skip unclassified meshes
            if cat_int == -1:
                continue

            # Threshold to extract this cat_int
            surface = (
                pv_volumetric_mesh.threshold(
                    [cat_int - 0.5, cat_int + 0.5], scalars=category_name
                )
                .extract_surface()
                # .triangulate()
                .clean()
            )

            surface_meshes[v["label"]] = {"mesh": surface, "rgb": v["rgb"]}

            srf_mesh_vertex_colors = np.tile(
                np.array(v["rgb"], dtype=np.uint8), (surface.n_points, 1)
            )
            surface.save(
                save_path / f"{cat_int}_{v['label']}.ply",
                texture=srf_mesh_vertex_colors,
            )

        return surface_meshes

    return (extract_threshold_surface_meshes,)


@app.cell
def _(Path, np):
    def extract_ghosted_surface_meshes(
        pv_volumetric_mesh,
        category_name: str,
        category_map: dict,
        save_path: Path | None = None,
    ) -> dict:
        unstructured_grid = pv_volumetric_mesh.cast_to_unstructured_grid()

        surface_meshes = {}
        for cat_int, v in category_map.items():
            cat_int = int(cat_int)
            ghosts = np.argwhere(unstructured_grid["facies"] != cat_int)
            ghosted_ugrid = unstructured_grid.remove_cells(ghosts)
            # Threshold to extract this cat_int
            surface = ghosted_ugrid.extract_surface().clean()

            surface_meshes[v["label"]] = {"mesh": surface, "rgb": v["rgb"]}

            if save_path:
                srf_mesh_vertex_colors = np.tile(
                    np.array(v["rgb"], dtype=np.uint8), (surface.n_points, 1)
                )
                surface.save(
                    save_path / f"{cat_int}_{v['label']}.ply",
                    texture=srf_mesh_vertex_colors,
                )

        return surface_meshes

    return (extract_ghosted_surface_meshes,)


if __name__ == "__main__":
    app.run()
