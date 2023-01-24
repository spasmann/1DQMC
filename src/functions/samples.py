# -*- coding: utf-8 -*-

import numpy as np
import math
from scipy.stats.qmc import Sobol, Halton, LatinHypercube
from src.functions.particle import Particle
from mpi4py import MPI
from functools import partial
# =============================================================================
# Class Initialization and Splitting for MPI
# =============================================================================
class Samples:
    """
    Class for generating list of Particles given various initial conditions.
    
    This will need to become more complex to return samples for different
    sources and sampling distributions.
    """
    def __init__(self, qmc_data, geometry, mesh):
        self.geometry       = geometry
        self.mesh           = mesh
        self.generator      = qmc_data.generator
        self.source_tilt    = qmc_data.source_tilt
        self.RQMC           = qmc_data.RQMC
        self.rng_seed       = qmc_data.rng_seed
        self.G              = qmc_data.G
        self.N              = qmc_data.N
        self.Nx             = qmc_data.Nx
        self.totalDim       = qmc_data.totalDim
        self.RB             = qmc_data.RB
        self.LB             = qmc_data.LB
        self.left           = qmc_data.left
        self.right          = qmc_data.right
        self.FixedSource    = qmc_data.FixedSource
        
        self.phi            = qmc_data.tallies.phi_avg
        
        # split the total number of particles into the different sources
        #self.Nleft = 0
        #self.Nright=0
        #self.Nvolumetric = self.N
        if (self.left):
            self.phi_left = qmc_data.phi_left
            #self.left = math.floor(0.125*self.N)
        if (self.right):
            self.phi_right = qmc_data.phi_right
            #self.right = math.floor(0.125*self.N)
            
        #self.Nvolumetric = self.N - self.Nright - self.Nleft
        # use MPI rank and nproc to determine which random numbers to use
        # each rank will generate the whole matrix, then use "start" and 
        # "stop" to grab the appropriate section
        comm        = MPI.COMM_WORLD
        rank        = comm.Get_rank()
        nproc       = comm.Get_size()
        self.rank   = comm.Get_rank()
        self.nproc  = comm.Get_size()
        self.start  = math.floor((rank/nproc)*self.N)
        self.stop   = math.floor((rank+1)/nproc*self.N) 
        
# =============================================================================
# Generate Particles
# =============================================================================
    def GenerateParticles(self, q, qdot):
        self.q       = q
        self.qdot    = qdot
        self.counter = 0
        self.GetRnMatrix()
        self.particles = []
        if (self.left):
            self.LeftBoundaryParticles()
            self.counter += 1
        if (self.right):
            self.RightBoundaryParticles()
            self.counter += 1
        self.VolumetricParticles()
        self.counter += 2 # used  to index the random number matrix 

    def VolumetricParticles(self):
        geo = self.geometry.geometry
        for i in range(self.start,self.stop):
            randX   = self.rng[i,self.counter]
            randMu  = self.rng[i,self.counter+1]
            x       = self.GetPos(randX) 
            mu      = self.GetMu(randMu)
            if (geo == "slab"):
                if (mu == 0.0):
                    mu += 0.01
                angle   = np.array((mu, 0, 0)) # mu, muSin, phi
                pos     = np.array((x,0,0)) # x, y, z
            if (geo == "cylinder"):
                randPhi = self.rng[i,self.counter+2]
                phi     = self.GetPhi(randPhi)
                muSin   = math.sqrt(1-mu**2)
                if (muSin == 0.0):
                    muSin += 0.01
                angle   = np.array((0, muSin, phi))
                pos     = np.array((0,0,x)) # x, y, z
            if (geo =="sphere"):
                if (mu == 0.0):
                    mu += 0.01
                randPhi = self.rng[i,self.counter+2]
                phi     = self.GetPhi(randPhi)
                muSin   = math.sqrt(1-mu**2)
                angle   = np.array((mu, muSin, phi))
                pos     = np.array((x,0,0)) # x, y, z
            zone     = self.mesh.GetZone(pos, angle)
            weight   = self.VolumetricWeight(zone, pos, self.mesh)
            particle = Particle(pos, angle, weight, zone)
            self.particles.append(particle)
            
    def RightBoundaryParticles(self):
        x = self.RB - 1e-9
        pos = np.array((x,0,0))
        zone = self.mesh.GetZone(pos, [0])
        weight = self.BoundaryWeight(self.phi_right)
        for i in range(self.start,self.stop):
            randMu = self.rng[i,self.counter]
            mu = -np.sqrt(randMu) - 1e-9
            angles = np.array((mu,0,0))
            particle = Particle(pos, angles, weight, zone)
            self.particles.append(particle)
            
    def LeftBoundaryParticles(self):
        x = self.LB + 1e-9
        pos = np.array((x,0,0))
        zone = self.mesh.GetZone(pos, [0])
        weight = self.BoundaryWeight(self.phi_left)
        for i in range(self.start,self.stop):
            randMu = self.rng[i,self.counter]
            mu = np.sqrt(randMu) + 1e-9
            angles = np.array((mu,0,0))
            particle = Particle(pos, angles, weight, zone)
            self.particles.append(particle)

# =============================================================================
# Generate LDS Matrix
# =============================================================================
    def RandomMatrix(self):
        np.random.seed(self.rng_seed)
        return np.random.random((self.N,self.totalDim))
    
    def SobolMatrix(self):
        sampler = Sobol(d=self.totalDim,scramble=self.RQMC, seed=self.rng_seed)
        m = round(math.log(self.N, 2))
        samples = sampler.random_base2(m=m)
        return samples
    
    def HaltonMatrix(self):
        sampler = Halton(d=self.totalDim,scramble=self.RQMC, seed=self.rng_seed)
        sampler.fast_forward(1)
        return sampler.random(n=self.N)
    
    def LatinHypercube(self):
        sampler = LatinHypercube(d=self.totalDim)
        return sampler.random(n=self.N)
    
    def GetRnMatrix(self):
        if (self.generator == "random"):
            self.rng = self.RandomMatrix()
        elif (self.generator == "sobol"):
            self.rng = self.SobolMatrix()
        elif (self.generator == "halton"):
            self.rng = self.HaltonMatrix()
        elif (self.generator == "latin_hypercube"):
            self.rng = self.LatinHypercube()
            
# =============================================================================
# Map Random Numbers to Physical Quantities
# =============================================================================
    def GetPos(self, randPos):
        return ((self.RB-self.LB)*randPos + self.LB)
    
    def GetMu(self, randMu):
        return (2*randMu - 1)
    
    def GetPhi(self, randPhi):
        return (2*math.pi*randPhi)
    
    def GetR(self,pos):
        return np.sqrt(sum(pos**2))

    def VolumetricWeight(self, zone, pos, mesh):
        x = pos[0]
        Q = self.q[zone,:] + self.FixedSource(x,zone)
        if (self.source_tilt):
            Q +=  self.qdot[zone,:]*(x - mesh.midpoints[zone])
        weight = Q*self.geometry.CellVolume(zone)/self.N*self.Nx
        return weight
    
    def BoundaryWeight(self, BV):
        # BV: boundary value, a.k.a phi_left or phi_right 
        return (self.geometry.SurfaceArea()*BV/self.N)