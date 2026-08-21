# modules/mod2Mobility/sizeParameters.py
# Author: Paula Spannring (BFW)
# Modified: Christoph Hesselbach (BFW)

import numpy as np
import math
import logging

import modules.mod0Helper.helpFunctions as helper

log = logging.getLogger("avaframe.ati.sizeParameters")


def praToVrel(ARel, dem, cfgSize):
    """
    calculate release Volume dependend on release area and elevation

    Parameters:
    -----------
    ARel: 2-dim numpy array or float
        area of PRA
    dem: 2-dim numpy array
        elevation values of PRAs
    cfgSize: congig Parser
        contains parameters for size parameterisation

    Returns:
    -----------
    VRel: numpy array or float
        Volume of release area
    """
    d = snowclimateToThickness(dem, cfgSize)
    VRel = ARel * d  # m³
    return VRel, d


def snowclimateToThickness(dem, cfgSize):
    """
    calculate snow thickness dependend on elevation and snow climate

    Parameters:
    -----------
    dem: 2-dim numpy array
        elevation values of PRAs
    cfgSize: congig Parser
        contains parameters for size parameterisation

    Returns:
    -----------
    d: numpy array or float
        snow thickness
    """
    if cfgSize.getboolean("constantPraThickness"):
        d = cfgSize.getfloat("praThickness")
    else:
        D0 = cfgSize.getfloat("D0")
        deltaD = cfgSize.getfloat("deltaD")
        d = D0 + deltaD * dem  # m
    return d


def praToVRelSize(ARel, dem, cfgSize):
    """
    calculate avalanche size dependend on release area and dem

    Parameters:
    -----------
    ARel: 2-dim numpy array or float
        area of PRA
    dem: 2-dim numpy array
        elevation values of PRAs
    cfgSize: congig Parser
        contains parameters for size parameterisation

    Returns:
    -----------
    size: numpy array or float
        avalanche size of PRA
    """

    ARel = np.array(ARel)

    if cfgSize.getboolean("constantPraThickness") == False:
        dem = np.array(dem)
        size = np.zeros(dem.shape)

        if len(dem.shape) > 1 and len(ARel.shape) > 1:
            # dem and pra are 2 dim
            for i, (z, pra) in enumerate(zip(dem, ARel)):
                for j, (z2, pra2) in enumerate(zip(z, pra)):
                    try:
                        d = snowclimateToThickness(z2, cfgSize)
                        size[i, j] = 2 + math.log(d * pra2 * 1e-3, 5)
                    except:
                        size[i, j] = 0

        elif len(dem.shape) > 1 and len(ARel.shape) == 0:
            # dem is 2 dimensional, ARel is float
            for i, z in enumerate(dem):
                for j, z2 in enumerate(z):
                    try:
                        d = snowclimateToThickness(z2, cfgSize)
                        size[i, j] = 2 + math.log(d * ARel * 1e-3, 5)
                    except:
                        size[i, j] = 0

        elif len(dem.shape) == 1 and len(ARel.shape) == 0:
            # dem is 1 dimensional, ARel is float
            for i, z2 in enumerate(dem):
                try:
                    d = snowclimateToThickness(z2, cfgSize)
                    size[i] = 2 + math.log(d * ARel * 1e-3, 5)
                except:
                    size[i] = 0

    else:
        praThickness = cfgSize.getfloat("praThickness")
        size = np.zeros(ARel.shape)

        vRel = praThickness * ARel
        if len(ARel.shape) == 1:
            for i, v in enumerate(vRel):
                try:
                    size[i] = 2 + math.log(v * 1e-3, 5)
                except:
                    size[i] = 0

        elif len(ARel.shape) > 1:
            for i, v in enumerate(vRel):
                for j, v2 in enumerate(v):
                    try:
                        size[i, j] = 2 + math.log(v2 * 1e-3, 5)
                    except:
                        size[i, j] = 0

        elif len(ARel.shape) == 0:
            size = 2 + math.log(vRel * 1e-3, 5)

    size = np.array(size)

    if cfgSize["sizeMax"] != "":
        sizeMax = cfgSize.getfloat("sizeMax")
        size[size > sizeMax] = sizeMax

    return size


def sizeToAlpha(size, dem, cfgSize):
    """
    calculate FlowPy input parameter alpha angle dependend on avalanche size
    the alpha angle decreases linearly with the avalanche size

    Parameters:
    -----------
    size: numpy array or float
        avalanche size of PRA cell
    dem: numpy array
        DEM, elevation
    cfgSize: congig Parser
        contains parameters for size parameterisation

    Returns:
    -----------
    alphaPRA: numpy array or float
        alpha angle of PRA
    """
    if cfgSize.getboolean("alphaDependendTemperature"):
        sizeTemp = sizeForParameterisation(
            size, dem, cfgSize, cfgSize.getfloat("sizeShiftAlpha")
        )
        log.info(
            f"The average of the change in size in the alpha parameterisation is: {np.nanmean(sizeTemp - size)}"
        )
    else:
        sizeTemp = size

    alphaSize2 = cfgSize.getfloat("alphaSize2")
    deltaAlpha = cfgSize.getfloat("deltaAlpha")

    alphaPRA = alphaSize2 - (sizeTemp - 2) * deltaAlpha
    return alphaPRA


def sizeToUmax(size, dem, cfgSize):
    """
    calculate FlowPy input parameter limit of maximal velocity dependend on avalanche size
    the uMax limit increases linearly with the avalanche size

    Parameters:
    -----------
    size: numpy array or float
        avalanche size of PRA cell
    dem: numpy array
        DEM, elevation
    cfgSize: congig Parser
        contains parameters for size parameterisation

    Returns:
    -----------
    umaxPRA: numpy array or float
        uMax limit of PRA
    """

    sizeTemp = sizeForParameterisation(
        size, dem, cfgSize, cfgSize.getfloat("sizeShiftUmax")
    )
    log.info(
        f"The average of the change in size in the uMax parameterisation is: {np.nanmean(sizeTemp - size)}"
    )

    uMaxSize2 = cfgSize.getfloat("uMaxSize2")
    deltaUMax = cfgSize.getfloat("deltaUMax")

    umaxPRA = uMaxSize2 + (sizeTemp - 2) * deltaUMax
    umaxPRA[umaxPRA < 5] = 5
    return umaxPRA


def sizeToExp(size, dem, cfgSize):
    """
    EXP parameter.
    If constantExp=True -> constant raster: base (dry) or base+shifted (wet, via sizeForParameterisation).
    Otherwise use size-dependent formula.
    """
    if cfgSize.getboolean("constantExp", fallback=False):
        base = cfgSize.getfloat("constantExpValue", fallback=12.0)

        if cfgSize.getboolean("alphaDependendTemperature", fallback=False):
            # Use same shifting logic as alpha/umax
            sizeTemp = sizeForParameterisation(
                size, dem, cfgSize, cfgSize.getfloat("sizeShiftExp", fallback=0.0)
            )
            delta = np.nanmean(sizeTemp - size)
            log.info(
                f"The average of the change in size in the EXP parameterisation is: {delta}"
            )

            return np.full_like(
                size, base + (delta if delta is not None else 0), dtype=np.float32
            )
        else:
            return np.full_like(size, base, dtype=np.float32)

    # ---- legacy size-dependent behaviour ----
    sizeTemp = sizeForParameterisation(
        size, dem, cfgSize, cfgSize.getfloat("sizeShiftExp", fallback=0.0)
    )
    expCoeff = cfgSize.getfloat("expCoeff")
    expBase = cfgSize.getfloat("expBase")
    exp = expCoeff * (expBase) ** sizeTemp
    return exp.astype(np.float32, copy=False)


def sizeForParameterisation(sizeRef, dem, cfgSize, wetSizeShift):
    """
    compute the shifted size as input for parameterisation - functions
    as function of temperature, with a cold and a warm limit

    Parameters:
    -----------
    sizeRef: numpy array or float
        avalanche size of PRA cell (for cold avalanches)
    dem: numpy array
        DEM
    cfgSize: congig Parser
        contains parameters for size parameterisation
    wetSizeShift: float
        maximal shift of size (for wet avalanches)

    Returns:
    -----------
    sizeTemp: numpy array
        shifted size inlcuding temperature
    """

    temp = zToTemp(cfgSize, dem)
    TCold = cfgSize.getfloat("TCold")
    TWarm = cfgSize.getfloat("TWarm")

    # compute the size as input for parameterisation as function of temperature
    slope = wetSizeShift / (TWarm - TCold)
    sizeTemp = sizeRef + (temp - TCold) * slope
    return sizeTemp


def zToTemp(cfgSize, dem):
    """
    compute temperature profile dependend on snow climate

    Parameters:
    -----------
    dem: numpy array
        DEM
    cfgSize: congig Parser
        contains parameters for size parameterisation

    Returns:
    -----------
    temp: numpy array
        temperature dependend on snow climate and dem
    """
    TCold = cfgSize.getfloat("TCold")
    TWarm = cfgSize.getfloat("TWarm")

    if cfgSize.getboolean("constantTemperature"):
        temp = cfgSize.getfloat("Tcons")
        temp = np.array(temp)
    else:
        T0 = cfgSize.getfloat("T0")
        deltaT = cfgSize.getfloat("deltaT")
        temp = T0 + dem * deltaT

    temp[temp < TCold] = TCold
    temp[temp > TWarm] = TWarm
    return temp


def alphaToSize(alphaSim, cfgSize):
    """
    Inverse of sizeToAlpha():
    Computes avalanche size from runout or travel angle

    Parameters:
    -----------
    alphaSim: numpy array or float
        simulated runout or travel angle
    cfgSize: congig Parser
        contains parameters for size parameterisation

    Returns:
    -----------
    sizeSim: numpy array or float
        avalanche size
    """

    alphaSize2 = cfgSize.getfloat("alphaSize2")
    deltaAlpha = cfgSize.getfloat("deltaAlpha")

    sizeSim = -(alphaSim - alphaSize2) / deltaAlpha + 2
    return sizeSim


def zDeltaToSize(zDeltaSim, cfgSize):
    """
    Inverse of sizeToAlpha():
    Computes avalanche size from runout or travel angle

    Parameters:
    -----------
    zDeltaSim: numpy array or float
        simulated zDelta
    cfgSize: congig Parser
        contains parameters for size parameterisation

    Returns:
    -----------
    sizeSim: numpy array or float
        avalanche size
    """
    uMaxSim = helper.zDelta2velocity(zDeltaSim)
    uMaxSize2 = cfgSize.getfloat("uMaxSize2")
    deltaUMax = cfgSize.getfloat("deltaUMax")

    sizeSim = (uMaxSim - uMaxSize2) / deltaUMax + 2
    return sizeSim


def zDeltaToDestructiveSize(zDeltaSim, cfgSize):
    """
    compute destructive size from zdelta (via impact pressure)

    Parameters:
    ------------
    zDeltaSim: np.array
        simulated zDelta (energy line height)
    cfgSize: configparser Parser
        contains parameters for size parameterisation

    Returns:
    sizeDestr: numpy array
        destructive size for each zDelta value
    """

    uMaxSim = helper.zDelta2velocity(zDeltaSim)

    # TODO: add a function that computes the density dependend on temperature (linearly??)
    # now we only compute density via Tcons
    if cfgSize.getfloat("Tcons") == -11:
        # dry avalanche
        rho = 200
    else:
        # wet avalanche
        rho = 400

    impressure = helper.velocity2pressure(uMaxSim, rho)

    sizeDestr = np.log10(impressure) * 2 - 0.5
    return sizeDestr


def travelLengthToRunoutSize(travelLength):
    """
    compute avalanche runout size from travel length

    Parameters:
    -----------
    travelLength: numpy array or float
        simulated runout or travel length

    Returns:
    -----------
    sizeSim: numpy array or float
        avalanche size
    """

    if np.any(travelLength <= 0):
        travelLength[travelLength <= 0] = 1e-3
    if np.any(travelLength > 2994):
        travelLength[travelLength > 2994] = 2994

    L = np.log(travelLength / 6.5) / np.log(1.5)
    sizeSim = (13 - np.sqrt(121 - 8 * L)) / 2

    return sizeSim


def affectedPathToSize(affectedPath, thickness=1):
    """
    compute deposition size from affected path,
    and using the technical scheme deposition volume - dimension size
    to compute the dimension size

    Parameters:
    ------------
    affectedPath: numpy array or float
        simulated affected path
    thickness: numpy array or float
        (deposition) thickness of affected path (default: 1 m)

    Returns:
    -----------
    sizeSim: numpy array or float
        avalanche size
    """

    depVolume = affectedPath * thickness

    sizeSim = np.log10(0.1 * depVolume)
    return sizeSim
