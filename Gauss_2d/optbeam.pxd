# -*- coding: utf-8 -*-
"""
file:    optbeam.pxd
brief:   ...
author:  Daniel Kotik
version: 1.5-beta
release date: xx.xx.2020
creation date: 03.04.2020
"""
cimport cython
from cpython.pycapsule cimport PyCapsule_New
from cpython cimport bool

# -----------------------------------------------------------------------------
# declare C functions as "cpdef" to export them to the module
# -----------------------------------------------------------------------------
cdef extern from "math.h":
    cpdef double _exp "exp" (double x) nogil
    cpdef double _sqrt "sqrt" (double x) nogil

cdef extern from "complex.h":
    cpdef double complex _cexp "cexp" (double complex z) nogil

# -----------------------------------------------------------------------------
# function declarations
# -----------------------------------------------------------------------------
cdef double _imag_1d_func_c(int n, double *arr, void *func_ptr)
cdef double _real_1d_func_c(int n, double *arr, void *func_ptr)

@cython.locals(real=cython.double, imag=cython.double, real_tol=cython.double,
               imag_tol=cython.double)
cdef (double complex, double, double) _complex_quad(func, double a, double b)

# -----------------------------------------------------------------------------
# class declarations
# -----------------------------------------------------------------------------
cdef class Beam2dCartesian:
    cdef:
        dict __dict__
        double x, _k
        public bool called

        double _ry, _rz

    cdef double spectrum(self, double k_y) nogil
    cdef double _phase(self, double k_y, double x, double y) nogil
    cdef double complex _integrand(self, double k_y) nogil

cdef class Gauss2d(Beam2dCartesian):
    cdef:
        double _W_y

    cdef double _f_Gauss(self, double k_y, double W_y) nogil
    cdef double spectrum(self, double k_y) nogil
