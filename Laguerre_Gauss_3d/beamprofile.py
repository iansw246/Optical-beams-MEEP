# -*- coding: utf-8 -*-
"""
file:    beamprofile.py
brief:   ...
author:  Daniel Kotik
version: 1.5-beta
release date: xx.xx.2020
creation date: 22.02.2020
"""
import cython
import math
import sys

from scipy.integrate import dblquad

if not cython.compiled:
    from math import sin, cos, exp
    from cmath import exp as cexp
    print("Please consider compiling `beamprofile.py` via Cython:\n\n"
          "     `$ cythonize -3 -i beamprofile.py`")


def real_func(x, y, func):
    """Return real part of function."""
    return func(x, y).real


def imag_func(x, y, func):
    """Return imag part of function."""
    return func(x, y).imag


def complex_dblquad(func, a, b, gfun, hfun):
    """Integrate real and imaginary part of the given function."""
    real, real_tol = dblquad(real_func, a, b, gfun, hfun, (func,))
    imag, imag_tol = dblquad(imag_func, a, b, gfun, hfun, (func,))

    return real + 1j*imag, real_tol, imag_tol


def f_Gauss_spherical(sin_theta, theta, phi, params):
    """2d-Gaussian spectrum amplitude.

    Impementation for spherical coordinates.
    """
    W_y, k = params['W_y'], params['k']

    return exp(-(k*W_y*sin_theta/2)**2)


def f_Laguerre_Gauss_spherical(sin_theta, theta, phi, params):
    """Laguerre-Gaussian spectrum amplitude.

    Impementation for spherical coordinates.
    """
    m = params['m']

    return f_Gauss_spherical(sin_theta, theta, phi, params) * theta**abs(m) * \
        cexp(1j*m*phi)


def psi_spherical(r, x, params):
    """Field amplitude function.

    Integration in spherical coordinates.
    """
    k, m = params['k'], params['m']

    if m == 0:
        f = f_Gauss_spherical
    else:
        f = f_Laguerre_Gauss_spherical

    try:
        getattr(psi_spherical, "called")
    except AttributeError:
        psi_spherical.called = True
        print("Calculating inital field configuration. "
              "This will take some time...")

    def phase(theta, phi, x, y, z):
        """Phase function."""
        sin_theta, sin_phi = sin(theta), sin(phi)
        cos_theta, cos_phi = cos(theta), cos(phi)

        return k*(sin_theta*(y*sin_phi - z*cos_phi) + cos_theta*x)

    def integrand(theta, phi):
        """..."""
        return sin(theta) * cos(theta) * \
            f(sin(theta), theta, phi, params) * \
            cexp(1j*phase(theta, phi, x, r.y, r.z))

    try:
        (result,
         real_tol,
         imag_tol) = complex_dblquad(integrand, 0, 2*math.pi, 0, math.pi/2)
    except Exception as e:
        print(type(e).__name__ + ":", e)
        sys.exit()

    return k**2 * result


def main():

    import meep as mp

    x, y, z = -2.15, 0.3, 0.5
    r = mp.Vector3(0, y, z)

    k1 = 31.41592653589793
    w_0 = 0.25464790894703254
    m_charge = 2

    params = dict(W_y=w_0, m=m_charge, k=k1)

    return lambda: psi_spherical(r, x, params)


if __name__ == '__main__':
    main()
