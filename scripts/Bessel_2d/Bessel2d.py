#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
file:    Airy2d.py
brief:   Python configuration input file for the FDTD solver Meep simulating the
         scattering of an incomplete Airy beam at a planar dielectric interface
author:  Daniel Kotik
version: 1.5-beta
release date: xx.xx.2020
creation date: 30.11.2019


invocation:

 a) launch the serial version of meep with specified polarisation (p)

        python3 Airy2d.py -s_pol False

 b) launch the parallel version of meep using 8 cores

        mpirun -quiet -np 8 python3 Airy2d.py

coordinate system in meep (defines center of computational cell):

                        --|-----> x
                          |
                          |
                          v y


visualisation:

Parenthesis show options for overlaying the dielectric function HDF5FILE_1.

      h5topng -S2 -X [SCALEX] -c hot (-a yarg -A [HDF5FILE_1]) [HDF5FILE_2]

If necessary, scale the x dimension of the image by SCALEX.

exmple use:
      h5topng -X 1.2 -Zc dkbluered -a yarg -A Airy2d-eps-___.h5 Airy2d-ez-___.h5

"""
# Set path to raw pyhton scripts rather than packacked version, for testing without needing to recompile
import os
import sys
# Insert path to optbeam source at front so the edited version is loaded rather than the official
# sys.path.insert(0, os.path.abspath("../../"))

import argparse
import math
import meep as mp
import optbeam as op

from datetime import datetime

print("Meep version:", mp.__version__)


def main(args):
    print("\nstart time:", datetime.now())

    # --------------------------------------------------------------------------
    # physical parameters characterizing light source and interface characteris-
    # tics (must be adjusted - eihter here or via command line interface (CLI))
    # --------------------------------------------------------------------------
    s_pol = args.s_pol
    ref_medium = args.ref_medium

    n1 = args.n1
    n2 = args.n2

    kw_0 = args.kw_0
    kr_w = args.kr_w

    # Bessel beam parameters
    theta = args.theta
    n = args.n

    # angle of incidence
    chi_deg = args.chi_deg
    #chi_deg = 1.0*op.critical(n1, n2)
    #chi_deg = 0.95*op.brewster(n1, n2)

    # --------------------------------------------------------------------------
    # specific Meep parameters (may need to be adjusted)
    # --------------------------------------------------------------------------
    sx = 10   # size of cell including PML in x-direction
    sy = 10   # size of cell including PML in y-direction
    pml_thickness = 0.25   # thickness of PML layer
    freq = 12      # vacuum frequency of source (4 to 12 is good)
    runtime = 90   # runs simulation for X times freq periods

    # number of pixels per wavelength in the denser medium (at least 10,
    # 20 to 30 is a good choice)
    pixel = 15

    # source position with respect to the center (point of impact) in Meep
    # units (-2.15 good); if equal -r_w, then source position coincides with
    # waist position
    #source_shift = 0
    source_shift = -0.4*(sx - 2*pml_thickness)

    # --------------------------------------------------------------------------
    # derived (Meep) parameters (do not change)
    # --------------------------------------------------------------------------
    k_vac = 2 * math.pi * freq
    k1 = n1 * k_vac
    n_ref = (1  if ref_medium == 0 else
             n1 if ref_medium == 1 else
             n2 if ref_medium == 2 else math.nan)
    r_w = kr_w / (n_ref * k_vac)
    w_0 = kw_0 / (n_ref * k_vac)
    shift = source_shift + r_w
    chi_rad = math.radians(chi_deg)

    params = dict(W_y=w_0, k=k1, theta=theta, n=n)

    # --------------------------------------------------------------------------
    # placement of the dielectric interface within the computational cell
    # --------------------------------------------------------------------------
    # helper functions
    def alpha(chi_rad):
        """Angle of inclined plane with y-axis in radians."""
        return math.pi/2 - chi_rad

    def Delta_x(alpha):
        """Inclined plane offset to the center of the cell."""
        sin_alpha = math.sin(alpha)
        cos_alpha = math.cos(alpha)
        return (sx/2) * (((math.sqrt(2) - cos_alpha) - sin_alpha) / sin_alpha)

    cell = mp.Vector3(sx, sy, 0)  # geometry-lattice
    default_material = mp.Medium(index=n1)
    geometry = [mp.Block(mp.Vector3(mp.inf, sx*math.sqrt(2), mp.inf),
                         center=mp.Vector3(+sx/2 + Delta_x(alpha(chi_rad)),
                                           -sy/2),
                         e1=mp.Vector3(1/math.tan(alpha(chi_rad)), 1, 0),
                         e2=mp.Vector3(-1, 1/math.tan(alpha(chi_rad)), 0),
                         e3=mp.Vector3(0, 0, 1),
                         material=mp.Medium(index=n2))]

    # --------------------------------------------------------------------------
    # add absorbing boundary conditions and discretize structure
    # --------------------------------------------------------------------------
    pml_layers = [mp.PML(pml_thickness)]
    resolution = pixel * (n1 if n1 > n2 else n2) * freq
    # set Courant factor (mandatory if either n1 or n2 is smaller than 1)
    Courant = (n1 if n1 < n2 else n2) / 2

    # --------------------------------------------------------------------------
    # display values of physical variables
    # --------------------------------------------------------------------------
    print()
    print("Specified variables and derived values:")
    print("n1:", n1)
    print("n2:", n2)
    print("chi:  ", chi_deg, " [degree]")
    print("incl.:", 90 - chi_deg, " [degree]")
    print("kw_0: ", kw_0)
    print("kr_w: ", kr_w)
    print("k_vac:", k_vac)
    print("polarisation:", "s" if s_pol else "p")
    print()

    # --------------------------------------------------------------------------
    # specify current source, output functions and run simulation
    # --------------------------------------------------------------------------
    force_complex_fields = False          # default: False
    eps_averaging = True                  # default: True
    filename_prefix = None

    # specify optical beam
    beam = op.Bessel2d(x=shift, params=params)

    sources = [mp.Source(src=mp.ContinuousSource(frequency=freq, width=0.5),
                         component=mp.Ez if s_pol else mp.Ey,
                         size=mp.Vector3(0, 9, 0),
                         center=mp.Vector3(source_shift, 0, 0),
                         amp_func=beam.profile
                         )
               ]

    sim = mp.Simulation(cell_size=cell,
                        boundary_layers=pml_layers,
                        default_material=default_material,
                        Courant=Courant,
                        geometry=geometry,
                        sources=sources,
                        resolution=resolution,
                        force_complex_fields=force_complex_fields,
                        eps_averaging=eps_averaging,
                        filename_prefix=filename_prefix
                        )

    sim.use_output_directory()   # put output files in a separate folder

    def eSquared(r, ex, ey, ez):
        """Calculate |E|^2.

        With |.| denoting the complex modulus if 'force_complex_fields?'
        is set to true, otherwise |.| gives the Euclidean norm.
        """
        return mp.Vector3(ex, ey, ez).norm()**2

    def output_efield2(sim):
        """Output E-field intensity."""
        name = "e2_s" if s_pol else "e2_p"
        func = eSquared
        cs = [mp.Ex, mp.Ey, mp.Ez]
        return sim.output_field_function(name, cs, func, real_only=True)

    sim.run(mp.at_beginning(mp.output_epsilon),
            mp.at_end(mp.output_efield_z if s_pol else mp.output_efield_y),
            mp.at_end(output_efield2),
            until=runtime)

    print("\nend time:", datetime.now())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-n1',
                        type=float,
                        default=1.0,
                        help=('index of refraction of the incident medium '
                              '(default: %(default)s)'))

    parser.add_argument('-n2',
                        type=float,
                        default=0.65,
                        help=('index of refraction of the refracted medium '
                              '(default: %(default)s)'))

    parser.add_argument('-s_pol',
                        type=bool,
                        default=True,
                        help=('True for s-spol, False for p-pol '
                              '(default: %(default)s)'))

    parser.add_argument('-ref_medium',
                        type=int,
                        default=0,
                        help=('reference medium: 0 - free space, '
                              '1 - incident medium, '
                              '2 - refracted medium (default: %(default)s)'))

    parser.add_argument('-kw_0',
                        type=float,
                        default=7,
                        help='beam width (>5 is good) (default: %(default)s)')

    parser.add_argument('-kr_w',
                        type=float,
                        default=0,
                        help=('beam waist distance to interface '
                              '(30 to 50 is good if source '
                              'position coincides with beam waist) '
                              '(default: %(default)s)'))

    parser.add_argument('-theta',
                        type=float,
                        default=30,
                        help='Bessel beam axicon angle in degrees (default: %(default)s)')

    parser.add_argument('-n',
                        type=float,
                        default=0,
                        help='Order of the Bessel beam (default: %(default)s)')

    parser.add_argument('-chi_deg',
                        type=float,
                        default=45,
                        help='incidence angle in degrees (default: %(default)s)')

    args = parser.parse_args()
    main(args)
