"""
msmapper plotting example

Create a 3D volumetric plot from a reciprocal space map of a peak

Requires a python environment with pyvista
 python -m pip install pyvista[jupyter]
"""

import numpy as np
import pyvista as pv
from mmg_toolbox import data_file_reader

file = '/dls/science/groups/das/ExampleData/hdfmap_tests/i16/processed/1109527_msmapper.nxs'

# Get reciprocal space data from file
remap = data_file_reader(file)
h, k, l, vol = remap('h_axis, k_axis, l_axis, volume')
# metadata
vol_hkl = np.array([h.mean(), k.mean(), l.mean()])
pixel_size = remap('/entry0/instrument/pil3_100k/module/fast_pixel_direction')  # float, mm
detector_distance = remap('/entry0/instrument/pil3_100k/transformations/origin_offset')  # float, mm
# average angle subtended by each pixel
solid_angle = pixel_size ** 2 / detector_distance ** 2  # sr
vol = vol * solid_angle


# Example: Create volumetric data
grid = pv.ImageData()
grid.dimensions = vol.shape
grid.spacing = (h[1]-h[0], k[1]-k[0], l[1]-l[0])
grid.origin = (h[0], k[0], l[1])
grid.point_data["values"] = vol.flatten(order='F')

# Create a plotter
plotter = pv.Plotter()
actor = plotter.add_volume(grid, cmap="viridis", opacity="sigmoid")

# Add a faint border (bounding box)
plotter.show_bounds(
    color="silver",      # border color
    grid=True,
    show_xaxis=True,    # optional: hide labels/ticks
    show_yaxis=True,
    show_zaxis=True,
    xtitle='h',
    ytitle='k',
    ztitle='l',
)

# Add colorscale sliders
init_min, init_max = actor.mapper.scalar_range
clim = [np.log10(init_min), np.log10(init_max)]
print(f"clim: {clim}")
crange = [0, np.log10(vol.max())]

eps = 1e-12  # small gap to keep min < max

def set_cmin(v):
    # ensure cmin < cmax
    clim[0] = min(float(v), clim[1] - eps)
    actor.mapper.scalar_range = (10**clim[0], 10**clim[1])
    plotter.render()

def set_cmax(v):
    # ensure cmax > cmin
    clim[1] = max(float(v), clim[0] + eps)
    actor.mapper.scalar_range = (10**clim[0], 10**clim[1])
    plotter.render()

# Use the full data range as slider bounds
plotter.add_slider_widget(
    set_cmin,
    rng=crange,
    value=clim[0],
    title="Min color limit",
    pointa=(0.10, 0.90),
    pointb=(0.90, 0.90),
    style='modern',
)

plotter.add_slider_widget(
    set_cmax,
    rng=crange,
    value=clim[1],
    title="Max color limit",
    pointa=(0.10, 0.75),
    pointb=(0.90, 0.75),
    style='modern',
)

plotter.show()

# Export interactive HTML (requires jupyter lab installed to use Panel)
# plotter.export_html("vtk_volume_plot.html")
# print("Interactive VTK volume plot saved as vtk_volume_plot.html")
