# -*- coding: utf-8 -*-

import numpy as np
from src.functions.material import Material
from src.functions.mesh import Mesh

class MultiGroupInit:
    def __init__(self, numGroups=12 ,N=2**12, Nx=20, generator="sobol"):
        
        if (numGroups != 12) and (numGroups != 70) and (numGroups != 618):
            raise ValueError("Number of groups must be 12, 70, or 618.")
        
        self.N                  = N
        self.Nx                 = Nx
        self.generator          = generator
        self.totalDim           = 2
        self.LB                 = 0
        self.RB                 = 500
        self.G                  = numGroups
        self.right              = False
        self.left               = False
        self.source             = np.ones((self.Nx,self.G))
        self.material_code      = numGroups
        self.geometry           = "slab"
        self.avg_scalar_flux    = True
        self.edge_scalar_flux   = False
        self.avg_angular_flux   = False
        self.avg_current        = False
        self.edge_current       = False
        self.shannon_entropy    = False
        self.moment_match       = False
        self.save_data          = True
        self.mesh               = Mesh(self.LB, self.RB, self.Nx)
        self.material           = Material(self.material_code, self.geometry, self.mesh)
        self.true_flux          = TrueFlux(self.material, self.source, self.Nx)
        self.phi_left           = 0.5*self.true_flux[0,:]
        self.phi_left           = np.reshape(self.phi_left, (1,self.G))
        self.phi_right          = 0.5*self.true_flux[0,:]
        self.phi_right          = np.reshape(self.phi_right, (1,self.G))

        

def TrueFlux(material, Q, Nx):
    """
    Analytic solution for infinite medium, slab, multigroup problem.
    Returns array of (Nx, G)
    """
    true_flux = np.dot(np.linalg.inv(np.diag(material.sigt[0,:]) - material.sigs[0,:,:]),Q[0,:])
    true_flux = np.tile(true_flux, (Nx,1))
    return true_flux



        