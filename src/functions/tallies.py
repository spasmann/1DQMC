# -*- coding: utf-8 -*-
import numpy as np
from scipy.integrate import quadrature


# =============================================================================
# Talies class
# =============================================================================

class Tallies:
    def __init__(self, qmc_data):
        self.flux = qmc_data.flux
        self.source_tilt = qmc_data.source_tilt
        self.Nr = qmc_data.Nx
        self.G = qmc_data.material.G
        self.q = qmc_data.fixed_source
        self.mode = qmc_data.mode
        self.qdot = None
        self.delta_flux = 1.0
        self.left = qmc_data.left
        if (self.left):
            self.phi_left = qmc_data.phi_left
        self.right = qmc_data.right
        if (self.right):
            self.phi_right = qmc_data.phi_right
        if (self.mode == "eigenvalue"):
            self.phi_f = np.random.uniform(size=(self.Nr, self.G))
        if (self.flux):
            # np.random.uniform(size=(self.Nr,self.G))
            self.phi_avg = np.ones((self.Nr, self.G))
            self.phi_avg_old = np.random.uniform(size=(self.Nr, self.G))
        if (self.source_tilt):
            self.dphi_s = np.random.uniform(size=(self.Nr, self.G))
            self.dphi_f = None
            self.qdot = np.zeros((self.Nr, self.G))
            if (self.mode == "eigenvalue"):
                self.dphi_f = np.random.uniform(size=(self.Nr, self.G))

# =============================================================================
# Tallies class functions
# =============================================================================

    def Tally(self, particle, material, geometry, mesh):
        if (self.flux):
            avg_scalar_flux(self.phi_avg, particle, material, geometry)
        if (self.source_tilt):
            avg_scalar_flux_derivative(self.phi_avg, self.dphi_s, particle,
                                       material, geometry, mesh)

    def DeltaFlux(self):
        self.delta_flux = np.linalg.norm(
            self.phi_avg - self.phi_avg_old, np.inf)

    def ResetPhiAvg(self):
        self.phi_avg = np.zeros((self.Nr, self.G))
        if (self.source_tilt):
            self.dphi_s = np.zeros((self.Nr, self.G))
            if (self.mode == "eigenvalue"):
                self.dphi_f = np.zeros((self.Nr, self.G))

# =============================================================================
# Tallies
# =============================================================================


def avg_scalar_flux(phi_avg, particle, material, geometry):
    zone = particle.zone
    G = material.G
    weight = particle.weight
    ds = particle.ds
    sigt = material.sigt[zone, :]
    sigt = np.reshape(sigt, (1, G))
    dV = geometry.CellVolume(zone)
    if (sigt.all() > 1e-12):
        phi_avg[zone, :] += (weight *
                             (1 - np.exp(-(ds * sigt))) / (sigt * dV))[0, :]
    else:
        phi_avg[zone, :] += (weight * ds / dV)


def avg_scalar_flux_derivative(phi, dphi, particle, material, geometry, mesh):
    if (geometry.geometry == "slab"):
        slab_integral(phi, dphi, particle, material, geometry, mesh)
    if (geometry.geometry == "cylinder"):
        cylinder_integral(dphi, particle, material, geometry, mesh)
        dphi[0, :] = 0
    if (geometry.geometry == "sphere"):
        sphere_integral(dphi, particle, material, geometry, mesh)
        dphi[0, :] = 0

# =============================================================================
# Geometry dependent functions
# =============================================================================

# analytic scheme


def slab_integral(phi, dphi, particle, material, geometry, mesh):
    zone = particle.zone
    mu = particle.angles[0]
    x = particle.pos[0]
    x_mid = mesh.midpoints[zone]
    dx = mesh.dx
    G = material.G
    w = particle.weight
    ds = particle.ds
    sigt = material.sigt[zone, :]
    sigt = np.reshape(sigt, (1, G))
    if (sigt.all() > 1e-12):
        a = mu * (w * (1 - (1 + ds * sigt) * np.exp(-sigt * ds)) / sigt**2)
        b = (x - x_mid) * (w * (1 - np.exp(-sigt * ds)) / sigt)
        dphi[zone, :] += (12 * (a + b) / dx**3)[0, :]
        # dphi[zone,:] += (12*(mu*(w*(1-(1+ds*sigt)*np.exp(-sigt*ds))/sigt**2)
        # + (x-x_mid)*(w*(1-np.exp(-sigt*ds))/sigt))/dx**3)[0,:]
    else:
        dphi[zone, :] += (mu * w * ds**(2) / 2 + w * (x - x_mid) * ds)

# numerical scheme
# def slab_integral(phi, dphi, particle, material, geometry, mesh):
#     zone    = particle.zone
#     G       = material.G
#     sigt    = material.sigt[zone,:]
#     sigt    = np.reshape(sigt, (1,G))

#     g = lambda z1,z2: ((phi[z1,:] - phi[z2,:])
#                         * (mesh.midpoints[z1] - mesh.midpoints[z2])
#                         / ((mesh.midpoints[z1]  - mesh.midpoints[z2])**2))
#     if (zone == 0):
#         m   = g(zone, zone+1)
#     if (zone == mesh.Nx-1):
#         m   = g(zone, zone-1)
#     else:
#         m1   = g(zone, zone+1)
#         m2   = g(zone, zone-1)
#         if (m1<m2):
#             m = m1
#         else:
#             m = m2
#     dphi[zone,:] = m


def cylinder_integral(dphi, particle, material, geometry, mesh):
    (mu, muSin, phi) = particle.angles
    (x, y, z) = particle.pos
    zone = particle.zone
    R_mid = mesh.midpoints[zone]
    dx = mesh.dx
    w = particle.weight[0]
    ds = particle.ds
    sigt = material.sigt[zone, :][0]

    def f(s): return (w * np.exp(-sigt * s) *
                      (np.sqrt((y + muSin * np.sin(phi) * s)**2
                               + (z + muSin * np.cos(phi) * s)**2) - R_mid))
    F = quadrature(f, 0, ds)
    dphi[zone, :] += F[0]


def sphere_integral(dphi, particle, material, geometry, mesh):
    (mu, muSin, phi) = particle.angles
    (x, y, z) = particle.pos
    zone = particle.zone
    R_mid = mesh.midpoints[zone]
    dx = mesh.dx
    w = particle.weight[0]
    ds = particle.ds
    sigt = material.sigt[zone, :][0]

    def f(s):
        a = (x + mu * s)**2
        b = (y + muSin * np.sin(phi) * s)**2
        c = (z + muSin * np.cos(phi) * s)**2
        return (w * np.exp(-sigt * s) * (np.sqrt(a + b + c) - R_mid))
    # print(ds)
    F = quadrature(f, 0.0, ds)
    dphi[zone, :] += F[0]
