#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun  7 13:17:55 2022

@author: sampasmann
"""
import numpy as np
from src.functions.sweep import Sweep
from src.functions.source import GetSource
from mpi4py import MPI


def SI_Map(phi_f, phi_s, qmc_data):
    """
    PI_Map(phi_f, phi_s, qmc_data)
    -----------------------

    """
    G = qmc_data.G
    Nx = qmc_data.Nx
    Nt = qmc_data.Nt
    Nv = int(Nx * G)
    if (qmc_data.source_tilt):
        qmc_data.tallies.dphi_s = np.reshape(phi_s[Nv:], (Nx, G))
        phi_s = phi_s[:Nv]
        phi_f = phi_f[:Nv]
    phi_s = np.reshape(phi_s, (Nx, G))
    phi_f = np.reshape(phi_f, (Nx, G))
    qmc_data.tallies.q = GetSource(phi_s, qmc_data, phi_avg_f=phi_f)
    # samples are gneratred with initialization of sweep
    sweep = Sweep(qmc_data)
    sweep.Run(qmc_data)  # QMC sweep
    phi_out = qmc_data.tallies.phi_avg
    phi_out = np.reshape(phi_out, (Nv, 1))
    if (qmc_data.source_tilt):
        dphi = qmc_data.tallies.dphi_s
        dphi = np.reshape(dphi, (Nv, 1))
        phi_out = np.append(phi_out, dphi)
        phi_out = np.reshape(phi_out, (Nt, 1))
    # all reduce phi_out here (they automatically wait for each other)
    comm = MPI.COMM_WORLD
    phi_out = comm.allreduce(phi_out, op=MPI.SUM)

    return phi_out


def RHS(qmc_data):
    """
    RHS(qmc_data)
    -------------
    We solve A x = b with a Krylov method. This function extracts
    b from Sam's qmc_data structure by doing a transport sweep with
    zero scattering term.
    """
    # G       = qmc_data.G
    Nt = qmc_data.Nt
    phi_f = qmc_data.tallies.phi_f
    zed = np.zeros((Nt, 1))
    if (qmc_data.source_tilt):
        dphi = qmc_data.tallies.dphi_s
        qmc_data.tallies.dphi_s = zed

    b = SI_Map(phi_f, zed, qmc_data)  # qmc_sweep with phi(0)

    if (qmc_data.source_tilt):
        qmc_data.tallies.dphi_s = dphi

    return b


def MatVec_data(qmc_data):
    """
    MXV_data(qmc_data)
    ------------------
    This function adds the right side of the linear system to Sam's
    qmc_data structure so I can pass it to the matrix-vector product.
    """
    b = RHS(qmc_data)
    global matvec_data
    matvec_data = [b, qmc_data]
    return matvec_data


def MatVec(phi_in):
    """
    MXV(phi_in)
    ---------------------
    We solve A x = b with a Krylov method. This function extracts the
    matrix-vector product A * phi_in from Sam's qmc_data structure by
    doing a transport sweep with zero boundary conditions and zero external
    source.
    """
    b = matvec_data[0]
    qmc_data = matvec_data[1]
    phi_f = qmc_data.tallies.phi_f
    Nt = qmc_data.Nt
    phi_in = np.reshape(phi_in, (Nt, 1))
    # qmc_data.source = np.zeros((Nx,G))
    axv = phi_in - (SI_Map(phi_f, phi_in, qmc_data) - b)

    return axv
