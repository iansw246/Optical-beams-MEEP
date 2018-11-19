#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
file:   plot_2d_matplotlib.py
brief:  Python script to visualise transverse intensity profiles of vortex beams.
        The program extracts 2d slices (for any given section) of an HDF5 file generated by the FDTD solver Meep.
author: Daniel Kotik
date:   18.01.2018

        It is highly recommended to feed this script with an HDF5 file of EVEN dimensions (this can be easily checked
        with the command 'h5ls e_imag2_mixed-000001500.h5' for example). Due to some internals of Meep, only with an
        appropriate choice of the 'pixel' and 'freq' parameters ensuring even dimensions a pefectly centered point of
        impact within the computaional cell is quaranteed.

        calculating data dimensions (N_x, N_y, N_z) from Meep parameters 'n1', 'n2', 'pixel' and 'freq':

            resolution = n1 * pixel * freq (if n1 > n2)
            resolution = n2 * pixel * freq (if n2 > n1)

            N_x = resolution * sx
            N_y = resolution * sy
            N_z = resolution * sz

        Variables which determine the properties of the slice are 'vec_length', 'delta_deg' (or 'WIDTH') and 'SLICE'.
"""
from scipy.ndimage import measurements

import matplotlib.pyplot as plt
import numpy as np
import h5py
import gc

# ------------------------------------------------------------------------------
# set parameters
# ------------------------------------------------------------------------------
# general parameters
# relative index of refraction
n = 1.50 / 1.0
# angle of incidence in degrees
chi_deg = 60  # 56.31
# inclination of the interface with respect to the x-axis
inc_deg = 90 - chi_deg

# Meep related parameters
sx, sy, sz = (5, 5, 5)
freq = 5
# cut off borders of data (remove PML layer up to and including line source
# placement)
cutoff = 20

# -----------------------------------------------------------------------------
# import data from HDF file(s)
# -----------------------------------------------------------------------------
# path = "simulations/LaguerreGauss3d-out_even/"
# path = "simulations/meep-A/LaguerreGauss3d_A-out/"  # focus on the transmitted beam
path = "simulations/meep-B/LaguerreGauss3d_B-out/"    # focus on the reflected beam

filename_real = path + "e_real2_mixed-000001500.h5" #"e_real2_s-000010.00.h5"
filename_imag = path + "e_imag2_mixed-000001500.h5" #"e_imag2_s-000010.00.h5"

with h5py.File(filename_real, 'r') as hf:
    # print("keys: %s" % hf.keys())
    data_real = hf[hf.keys()[0]][:]

with h5py.File(filename_imag, 'r') as hf:
    # print("keys: %s" % hf.keys())
    data_imag = hf[hf.keys()[0]][:]

data = data_real + data_imag
del data_imag                                       # free memory early

orig_shape = np.shape(data)

print("file size in MB: ", np.round(data.nbytes / 1024 / 1024, 2))
print("data (max, min): ", (np.round(data.max(), 2), np.round(data.min(), 2)))
print(" original shape: ", orig_shape)

data = data[cutoff:-cutoff, cutoff:-cutoff, cutoff:-cutoff] / data.max()
new_shape = np.shape(data)
print("      new shape: ", new_shape)

# calculate center of 3d data array in floating(!) pixel coordinates
# if all dimensions are even numbers:
#center = tuple((np.asarray(new_shape) - 1) / 2)
# if all dimensions are odd numbers:
#center = tuple((np.asarray(new_shape) - 0) / 2)
center = []

for i in [0, 1, 2]:
    N = new_shape[i]
    if not N % 2:                                  # check if N is even
        center.extend([(N - 1) / 2])
    else:
        center.extend([N / 2])


# conversion between pixel coordinates and dimensionless (kX, ky, kZ)
# coordinates (wrt the incident medium)
def dimless_coord(pixel_coord, center_pixel_coord=0):
    """Conversion from pixel coordinates to dimensionless coordinates."""
    return sx * 2 * np.pi * freq / (orig_shape[0] - 1) * (pixel_coord
                                                          - center_pixel_coord)


def pixel_coord(dimless_coord):
    """Conversion from dimensionless coordinates to pixel coordinates."""
    return (orig_shape[0] - 1) / (sx * 2 * np.pi * freq) * dimless_coord


# ------------------------------------------------------------------------------
# calculating propagation directions of the sec. beams accor. to geom. optics
# ------------------------------------------------------------------------------
# angle of refraction in radians
eta_rad = np.arcsin((1.0 / n) * np.sin(np.deg2rad(chi_deg)))

# properties of the k-vectors
kw_0 = 10
# Rayleigh length
kD = (kw_0 ** 2) / 2.0
# propagation distance given in dimensionless coordinates
kZ = kD
# propagation distance given in pixel coordinates
vec_length = pixel_coord(kZ)

# degree to radians conversion
chi_rad = np.deg2rad(chi_deg)
inc_rad = np.deg2rad(inc_deg)

vec_inc = (int(center[0] - vec_length), int(center[1]))
vec_ref = (int(center[0] + round(vec_length * np.sin(chi_rad - inc_rad))),
           int(center[1] + round(vec_length * np.cos(chi_rad - inc_rad))))
vec_tra = (int(center[0] + round(vec_length * np.sin(eta_rad + inc_rad))),
           int(center[1] - round(vec_length * np.cos(eta_rad + inc_rad))))

components = [vec_inc, vec_ref, vec_tra]

# ------------------------------------------------------------------------------
# obtaining cut-plane data position
# ------------------------------------------------------------------------------
# half opening angle (0 - 90 degrees)
delta_deg = 35

# degree to radians conversion
delta_rad = np.deg2rad(delta_deg)

# calculating start and endpoints of the cut-planes wtr to a centered
# coordinate system (Meep cs)
inc_x = lambda delta: -vec_length
inc_y = lambda delta:  vec_length * np.tan(delta)

ref_x = lambda delta:  (vec_length / np.cos(delta)) * np.sin(chi_rad
                                                             + delta - inc_rad)
ref_y = lambda delta:  (vec_length / np.cos(delta)) * np.cos(chi_rad
                                                             + delta - inc_rad)

tra_x = lambda delta:  (vec_length / np.cos(delta)) * np.sin(eta_rad
                                                             + delta + inc_rad)
tra_y = lambda delta:  (vec_length / np.cos(delta)) * np.cos(eta_rad
                                                             + delta + inc_rad)

cut_inc = (int(center[0] + inc_x(0)), np.floor(center[1]
                                               + round(inc_y(-delta_rad))),
           int(center[0] + inc_x(0)), np.ceil(center[1]
                                              + round(inc_y(delta_rad))))

cut_ref = (int(center[0] + round(ref_x( delta_rad))), np.floor(center[1]
                                                               + round(ref_y( delta_rad))),
           int(center[0] + round(ref_x(-delta_rad))), np.ceil(center[1]
                                                              + round(ref_y(-delta_rad))))

cut_tra = (int(center[0] + round(tra_x(-delta_rad))), np.floor(center[1] - round(tra_y(-delta_rad))),
           int(center[0] + round(tra_x( delta_rad))), np.ceil( center[1] - round(tra_y( delta_rad))))

# special cut-plane for the half of the transmitted beam placed at the origin
# reamark: the x0 and x1 components are shifted by one pixel towards the
#          secondary medium ensuring that only data values of the transmitted
#          beam are taken into account
WIDTH = int(pixel_coord(40))
cut_hal = (int(center[0]) + 1,  int(center[1]),
           int(center[0]) + 1 - int(round(WIDTH * np.cos(eta_rad + inc_rad))),
           int(center[1]) - int(round(WIDTH * np.sin(eta_rad + inc_rad))))

SLICE = "cut_ref"                                  # choose which slice to use

x0, y0, x1, y1 = eval(SLICE)

width = int(np.hypot(x1 - x0 + 1, y1 - y0 + 1))    # width of the cut-plane (determined by vec_length together with
                                                   # delta_deg or just by WIDTH)

x, y  = np.linspace(x0, x1, width, dtype=np.int), np.linspace(y0, y1, width, dtype=np.int)

if SLICE == "cut_hal":
    z = np.linspace(np.floor(center[2] - (width - 1)),
                    np.ceil( center[2] + (width - 1)), 2 * width, dtype=np.int)
else:
    z = np.linspace(np.floor(center[2] - round(vec_length * np.tan(delta_rad))),
                    np.ceil( center[2] + round(vec_length * np.tan(delta_rad))), width, dtype=np.int)

# restrict cut-plane indices to values within the bound of the data array
valid_x = np.logical_and(0 <= x, x < new_shape[0])
valid_y = np.logical_and(0 <= y, y < new_shape[1])
valid = np.logical_and(valid_x, valid_y)
data_cut = data[x[valid], y[valid], :]
# make data_cut having equal dimensions
data_cut = data_cut[:, z]
cut_shape = np.shape(data_cut)

print("   cutted shape: ", cut_shape)

# ------------------------------------------------------------------------------
# visualising
# ------------------------------------------------------------------------------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))

## visualise intensity distribution within the plane of incidence
data_poi = data[:, :, int(center[2])]               # slice within the plane of incidence
extent_poi_dimless = [dimless_coord(0, center[0]), dimless_coord(new_shape[0] - 1, center[0]),
                      dimless_coord(0, center[1]), dimless_coord(new_shape[1] - 1, center[1])]

ax1.imshow(np.transpose(data_poi), origin="lower", cmap=plt.cm.hot, interpolation='None', extent=extent_poi_dimless)

## visualise k-vectors within the plane of incidence
for i in [0, 1, 2]:
    ax1.plot([dimless_coord(center[0], center[0]), dimless_coord(components[i][0], center[0])],
             [dimless_coord(center[1], center[1]), dimless_coord(components[i][1], center[1])], '--', color="white")

## visualise cut-line
ax1.plot([dimless_coord(x0, center[0]), dimless_coord(x1, center[0])],
         [dimless_coord(y0, center[1]), dimless_coord(y1, center[1])], 'ro-')

## subfigure properties
ax1.set_title("plane of incidence")
ax1.set_xlabel(r"$kZ^i$")
ax1.set_ylabel(r"$kX^i$")

## visualise transverse intensity distribution with respect to the axis of the respective central wave vector
## extent_cut_dimless = [ky_min, ky_max, kX_min, kX_max]
X_max_pixel_coord = cut_shape[0] - 1
y_max_pixel_coord = cut_shape[1] - 1

extent_cut_dimlessA = [dimless_coord(0, y_max_pixel_coord / 2), dimless_coord(y_max_pixel_coord, y_max_pixel_coord / 2),
                       dimless_coord(0, X_max_pixel_coord / 2), dimless_coord(X_max_pixel_coord, X_max_pixel_coord / 2)]

extent_cut_dimlessB = [dimless_coord(0, y_max_pixel_coord / 2), dimless_coord(y_max_pixel_coord, y_max_pixel_coord / 2),
                       dimless_coord(0, X_max_pixel_coord / 1), dimless_coord(X_max_pixel_coord, X_max_pixel_coord / 1)]

if SLICE == "cut_hal":
    ax2.imshow(data_cut, origin="upper", cmap=plt.cm.gist_stern_r, interpolation='None', aspect='equal',
                         extent=extent_cut_dimlessB)
else:
    ax2.imshow(data_cut, origin="lower", cmap=plt.cm.gist_stern_r, interpolation='None', aspect='equal',
                         extent=extent_cut_dimlessA)

## visualise geometric center point (floating pixel coordinates)
#ax2.axvline(center[2], color='w', lw=0.5)
#ax2.axhline(int((width - 1) / 2 - np.arange(width)[valid][0]), color='w', lw=0.5)

## visualise geometric center point (dimensionless coordinates)
ax2.axvline(0, color='w', lw=0.5)
ax2.axhline(0, color='w', lw=0.5)

## calculate center of mass
labels_center = measurements.center_of_mass(data_cut)

if SLICE == "cut_hal":
    kX_c = 0.0
else:
    kX_c = dimless_coord(labels_center[0], (cut_shape[0] - 1) / 2)

ky_c = dimless_coord(labels_center[1], (cut_shape[1] - 1) / 2)

print("center (kX, ky):  (%.3f, %.3f)" % tuple(np.round((kX_c, ky_c), 3)))

## visualise center of mass (dimensionless coordinates)
ax2.axhline(kX_c, color='red', linestyle = "dashed", dashes=(10,5), lw=0.5)
ax2.axvline(ky_c, color='red', linestyle = "dashed", dashes=(10,5), lw=0.5)

## visualise center of mass (floating pixel coordinates)
#ax2.axhline(labels_center[0], color='red', linestyle = "dashed", dashes=(10,5), lw=0.5)
#ax2.axvline(labels_center[1], color='red', linestyle = "dashed", dashes=(10,5), lw=0.5)

## subfigure properties
ax2.set_title("cut-plane")
ax2.set_xlabel(r"$ky$")
ax2.set_ylabel(r"$kX$")

plt.tight_layout()
plt.show()

## free memory
try:
    del data, data_poi, data_real, data_cut
except:
    pass

gc.collect()                                        # run garbage collector
