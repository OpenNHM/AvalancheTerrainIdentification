"""
Tools/ help functions for regional thalweg plots
"""

import numpy as np
import pathlib
import geopandas as gpd
import logging
import os
import pickle


import avaframe.in1Data.getInput as gI
import avaframe.in2Trans.rasterUtils as rasterUtils
import avaframe.in3Utils.geoTrans as gT

# create local logger
log = logging.getLogger("avaframe.modules.regionalThalwegTools")


def searchResFolder(avalanchedir, module="com4FlowPy"):
    """
    search the results folders (res_<simHash>) of a module

    Parameters
    -----------
    avalanchedir: pathlib Path
        avalanche directory
    module: str
        module name

    Returns
    -----------
    oneResFolder: bool
        True if there is exactly one results folder
    simHash: str
        simulation hash if there is exactly one results folder, otherwise ""
    """
    peakFilesDir = avalanchedir / "Outputs" / module / "peakFiles"

    resFolders = []
    for filename in os.listdir(peakFilesDir):
        if filename.startswith("res_"):
            resFolders.append(filename)
    if len(resFolders) == 0:
        message = f"No results {module} folder found in {peakFilesDir}"
        log.error(message)
        raise FileNotFoundError(message)
    elif len(resFolders) > 1:
        oneResFolder = False
        simHash = ""
    elif len(resFolders) == 1:
        oneResFolder = True
        simHash = str(resFolders[0]).split("res_", 1)[1]
    return oneResFolder, simHash


def getRasterFile(path, variable="", ext=""):
    """
    search for raster (*.asc or *.tif) that contains a given variable in the filename
     if "ext" is given then search for that extent


    Parameters:
    -----------
    path: pathlib.Path
        path to raster file or folder containing raster
    variable: str
        part that is searched for (is contained in file name)
    ext: str
        extent of file

    Returns:
    -----------
    filePath: pathlib Path
        path to raster file in the folder
    """
    path = pathlib.Path(path)

    if path.is_file():
        filePath = path
    else:
        if ext == "":
            files = sorted(list(path.glob(f"*{variable}.asc")))
            if len(files) == 0:
                files = sorted(list(path.glob(f"*{variable}.tif")))
            if len(files) == 0:
                message = f"No raster file with {variable} found in {path}."
                # log.error(message)
                raise FileNotFoundError(message)
            filePath = files[0]
        else:
            files = sorted(list(path.glob(f"*{variable}.{ext}")))
            if len(files) == 0:
                message = f"No {ext} file with {variable} and found in {path}."
                log.info(message)
                filePath = ""
            else:
                filePath = files[0]
    return filePath


def getMaxZDeltaInput(dataThalweg):
    """get the input zDelta maximum (FlowPy input parameter) from the thalweg data

    The key is "zDeltaMaxInput" in the thalweg pickle files. In older files the input value
    is saved as (scalar) "zDeltaMax"; in newer files "zDeltaMax" is the array of the
    maximum zDelta per generation and therefore not used here.

    Parameters
    -----------
    dataThalweg: dict
        thalweg data loaded from the thalweg pickle file

    Returns
    -----------
    zDeltaMaxInput: float
        input zDelta maximum [m]
    """
    if "zDeltaMaxInput" in dataThalweg:
        return dataThalweg["zDeltaMaxInput"]
    if "zDeltaMax" in dataThalweg and np.ndim(dataThalweg["zDeltaMax"]) == 0:
        return dataThalweg["zDeltaMax"]
    message = (
        "Input zDelta maximum not found in thalweg data: neither 'zDeltaMaxInput' "
        "nor a scalar 'zDeltaMax' (older thalweg files) is available."
    )
    log.error(message)
    raise KeyError(message)


# TODO: leave this zdelta-type option like this??
# valid options of cfg["GENERAL"]["zDeltaThalweg"] with their plot label and output file name suffix
ZDELTA_THALWEG_TYPES = {
    "averaged": {"label": "averaged per generation", "fileSuffix": "zdAvgGen"},
    "maxGeneration": {"label": "max. per generation", "fileSuffix": "zdMaxGen"},
    "raster": {"label": "from result raster", "fileSuffix": "zdRaster"},
}


def getZDeltaLabel(zDeltaType):
    """get the plot label (description) of the simulated zDelta type"""
    return ZDELTA_THALWEG_TYPES[zDeltaType]["label"]


def getZDeltaFileSuffix(zDeltaType):
    """get the output file name suffix of the simulated zDelta type"""
    return ZDELTA_THALWEG_TYPES[zDeltaType]["fileSuffix"]


def getSimulatedZDeltaAveraged(dataThalweg, zDeltaType, pathToOutput):
    """get the simulated zDelta along the averaged (not extended) thalweg, one value per generation

    Parameters
    -----------
    dataThalweg: dict
        thalweg data saved by com4FlowPy (averaged thalweg, one value per generation)
    zDeltaType: str
        averaged: flux weighted average zDelta of every generation (key "zdelta" or "zDelta")
        maxGeneration: maximum zDelta of every generation (key "zDeltaMax", array)
        raster: values of the zdelta result raster at the averaged thalweg coordinates
    pathToOutput: pathlib Path
        path to the simulation results (with the zdelta raster), only needed for raster

    Returns
    -----------
    zDelta: numpy array
        simulated zDelta along the averaged thalweg
    """
    if zDeltaType == "averaged":
        key = "zdelta" if "zdelta" in dataThalweg else "zDelta"
        return np.asarray(dataThalweg[key], dtype=float)

    if zDeltaType == "maxGeneration":
        if "zDeltaMax" not in dataThalweg or np.ndim(dataThalweg["zDeltaMax"]) == 0:
            message = (
                "The maximum zDelta per generation ('zDeltaMax') is not saved in the thalweg data. "
                "Add 'zDeltaMax' to thalwegVariables in the com4FlowPy configuration and rerun the "
                "simulation, or choose another zDeltaThalweg option."
            )
            log.error(message)
            raise KeyError(message)
        return np.asarray(dataThalweg["zDeltaMax"], dtype=float)

    if zDeltaType == "raster":
        zDeltaRasterFile = getRasterFile(pathToOutput, variable="zdelta")
        return np.asarray(
            getThalwegValuesFromRaster(zDeltaRasterFile, dataThalweg["x"], dataThalweg["y"]), dtype=float
        )
    message = f"zDeltaThalweg = {zDeltaType} is not valid, choose one of {list(ZDELTA_THALWEG_TYPES)}."
    log.error(message)
    raise ValueError(message)


def addSimulatedZDeltaToExtended(dataThalweg, profileExtended, zDeltaType, pathToOutput):
    """add the simulated zDelta (key "zdelta") to the extended thalweg profile

    Parameters
    -----------
    dataThalweg: dict
        thalweg data saved by com4FlowPy (averaged thalweg, one value per generation)
    profileExtended: dict
        extended (resampled) thalweg profile
    zDeltaType: str
        averaged: flux weighted average zDelta of every generation (key "zdelta")
        maxGeneration: maximum zDelta of every generation (key "zDeltaMax", array)
        raster: values of the zdelta result raster along the extended thalweg
    pathToOutput: pathlib Path
        path to the simulation results (with the zdelta raster)

    Returns
    -----------
    profileExtended: dict
        extended profile with the simulated zDelta ("zdelta") and its type ("zdeltaType")
    """
    if zDeltaType == "raster":
        zDeltaRasterFile = getRasterFile(pathToOutput, variable="zdelta")
        profileExtended["zdelta"] = getThalwegValuesFromRaster(
            zDeltaRasterFile, profileExtended["x"], profileExtended["y"]
        )
    else:
        averagedProfile = dict(dataThalweg)
        averagedProfile["zdelta"] = getSimulatedZDeltaAveraged(dataThalweg, zDeltaType, pathToOutput)

        profileExtended = interpolateValueFromAveragedToExtended(
            averagedProfile,
            profileExtended,
            "zdelta",
            startValue=0,
            endValue=0,
            indStart=profileExtended["indStartMassAverage"],
            indEnd=profileExtended["indEndMassAverage"],
        )
    # effective max. zDelta along the averaged thalweg (as in getEffectiveValues)
    zDeltaAveraged = getSimulatedZDeltaAveraged(dataThalweg, zDeltaType, pathToOutput)
    if zDeltaAveraged.size > 0 and not np.all(np.isnan(zDeltaAveraged)):
        profileExtended["zdeltaEffMax"] = np.nanmax(zDeltaAveraged)
    else:
        profileExtended["zdeltaEffMax"] = np.nan
    profileExtended["zdeltaType"] = zDeltaType
    return profileExtended


def cleanExtendedProfile(profileExtended):
    """
    remove the arrays of the averaged thalweg (one value per generation, e.g. travelLength, gamma,
    zDeltaMax) from the extended profile; only the point arrays and scalar
    values (e.g. alpha, exponent, zDeltaMaxInput, indStartMassAverage) are kept

    Parameters
    -----------
    profileExtended: dict
        extended thalweg profile

    Returns
    -----------
    profileCleaned: dict
        extended profile without the per-generation arrays
    """
    profileCleaned = {}
    removed = []
    for key, value in profileExtended.items():
        if key in ["x", "y", "z", "s", "zdelta"] or np.ndim(value) == 0:
            profileCleaned[key] = value
        else:
            removed.append(key)
    if removed:
        log.debug(f"Removed per-generation arrays from the extended profile: {removed}")
    return profileCleaned


def zDelta2velocity(zDelta):
    """compute velocity from energy line height

    Parameters
    -----------
    zDelta: numpy float or array
        energy line height

    Returns
    -----------
    velocity: numpy float or array
        velocity comuted frm zDelta
    """
    velocity = (zDelta * 2 * 9.81) ** 0.5
    return velocity


def velocity2pressure(velocity, rho):
    """compute pressure from velocity

    Parameters
    --------------
    velocity: numpy float or array
        velocity values
    rho: float
        density of snow

    Returns
    ----------------
    imppressure: numpy float or array
        computed pressure
    """
    pressure = rho * velocity**2 * 1e-3
    return pressure


def pressure2velocity(pressure, rho):
    """compute velocity from impact pressure (inverse of velocity2pressure)

    Parameters
    --------------
    pressure: numpy float or array
        pressure values [kPa]
    rho: float
        density of snow

    Returns
    ----------------
    velocity: numpy float or array
        velocity corresponding to the given pressure
    """
    velocity = np.sqrt(pressure * 1e3 / rho)
    return velocity


def readThalwegData(path, titleDict):
    """
    load thalweg data

    Parameters:
    -----------
    path: pathlib.Path
        OutputPath of the FlowPy simulation
    titleDict: dict
        contains

    Returns:
    -----------
    data: dict
        thalweg data of one thalweg
    filePath: pathlib Path
        path to the thalweg data file
    """
    centerOf = titleDict["centerOf"]
    startRow = titleDict["startRow"]
    startCol = titleDict["startCol"]
    relId = titleDict["relId"]

    if startRow != "":
        filePath = pathlib.Path(path) / f"thalwegData_{centerOf}_{startRow}_{startCol}.pickle"
        thalwegName = f"start cell with row {startRow} and column {startCol}"
    else:
        filePath = pathlib.Path(path) / f"thalwegData_{centerOf}_{relId}.pickle"
        thalwegName = f"release area id {relId}"
    if filePath.is_file():
        data = np.load(filePath, allow_pickle="TRUE")
    else:
        message = f"No thalweg data averaged with {centerOf} exist for {thalwegName} in {path}"
        log.error(message)
        raise FileNotFoundError(message)
    return data, filePath


def getOutFileNamePartly(titleDict, allThalwegs=False):
    """
    make name for outputfile

    Paramaters
    -------------
    titleDict: dict
        contains parameters of avalanche path
    allThalwegs: bool
        if True, no specification for one path is used

    Returns
    -------------
    outFileNamePart: str
        name for outputfile
    """
    centerOf = titleDict["centerOf"]
    startRow = titleDict["startRow"]
    startCol = titleDict["startCol"]
    relId = titleDict["relId"]
    simhash = titleDict["simHash"]

    if allThalwegs:
        outFileNamePart = f"{simhash}_{centerOf}"
    elif relId != "":
        outFileNamePart = f"{simhash}_{centerOf}_{relId}"
    else:
        outFileNamePart = f"{simhash}_{centerOf}_{startRow}_{startCol}"

    return outFileNamePart


def interpolateValueFromAveragedToExtended(
    averagedProfile, extendedProfile, variable, startValue=0.0, endValue=0.0, indStart=None, indEnd=None
):
    """
    Interpolate a variable from the averaged profile to the extended profile.

    The variable is interpolated from the averaged profile onto the resampled
    extended profile using the cumulative distance s. Only the section between
    indStart and indEnd is interpolated. Values before indStart are set to
    startValue and values after indEnd are set to endValue.

    Parameters
    ----------
    averagedProfile : dict
        Dictionary containing the averaged profile. Must contain the cumulative
        distance "s" and the variable specified by variable.
    extendedProfile : dict
        Dictionary containing the extended, resampled profile. Must contain the
        cumulative distance "s". The interpolated variable is added to this
        dictionary.
    variable : str
        Name of the variable to interpolate.
    startValue : float, optional
        Value assigned to all points before indStart. Default is 0.0.
    endValue : float, optional
        Value assigned to all points after indEnd. Default is 0.0.
    indStart : int, optional
        Index of the first point in extendedProfile for which interpolation
        is performed. If None, interpolation starts at the beginning of the
        profile.
    indEnd : int, optional
        Index of the last point (inclusive, as indEndMassAverage) in extendedProfile
        for which interpolation is performed. If None, interpolation is performed
        until the end of the profile.

    Returns
    -------
    dict
        The extendedProfile dictionary with the interpolated variable stored
        under the key specified by variable.
    """

    sAvg = averagedProfile["s"]
    varAvg = averagedProfile[variable]
    sExt = extendedProfile["s"]

    # Default to the whole profile
    if indStart is None:
        indStart = 0
    if indEnd is None:
        indEnd = len(sExt) - 1
    # indEnd is inclusive
    indStop = indEnd + 1

    # Allocate output and fill with boundary values
    varExt = np.full(len(sExt), endValue, dtype=float)
    varExt[:indStart] = startValue

    # Interpolate only on the requested section
    sExtShort = sExt[indStart:indStop]
    if len(sExtShort) >= 1:
        sExtShort = sExtShort - sExtShort[0]

    if len(sAvg) > 1:
        varExt[indStart:indStop] = np.interp(
            sExtShort,
            sAvg,
            varAvg,
            left=startValue,
            right=endValue,
        )

    extendedProfile[variable] = varExt

    return extendedProfile


def getThalwegValuesFromRaster(rasterFile, x, y, interp="bilinear"):
    """
    project thalweg coordinates to raster and extract values

    Parameters
    ----------
    rasterFile : str
        path to raster file
    x: np array
        x coordinates of thalweg
    y: np array
        y coordinates of thalweg
    interp: str
        interpolation method: "bilinear" or "nearest" (e.g. for raster containing ids)

    Returns
    ------------
    thalwegValues: np array
        values along thalweg read from raster
    """
    rasterDict = rasterUtils.readRaster(rasterFile)
    header = rasterDict["header"]
    rasterValues = rasterDict["rasterData"]
    rasterValues = np.where(rasterValues > 0, rasterValues, 0)

    thalwegValues, _ = gT.projectOnGrid(
        x,
        y,
        rasterValues,
        csz=header["cellsize"],
        xllc=header["xllcenter"],
        yllc=header["yllcenter"],
        interp=interp,
    )
    return thalwegValues


def getPathPolygons(pathToOutput):
    """read the process path polygons (one per release area, column PRA_id) written by com4FlowPy

    Parameters
    --------------
    pathToOutput: pathlib Path
        path to the simulation results

    Returns
    --------------
    pathPolygons: geopandas GeoDataFrame or None
        process path polygons, None if no *_pathPolygons.geojson exists
    """
    pathPolygonFiles = sorted(pathlib.Path(pathToOutput).glob("*_pathPolygons.geojson"))
    if len(pathPolygonFiles) == 0:
        log.warning(
            f"No *_pathPolygons.geojson found in {pathToOutput}, the process path is taken from the flux raster."
        )
        return None
    polygons = gpd.read_file(pathPolygonFiles[0])
    return polygons


def getRelIdFromThalwegFile(fileName):
    """get the release area id from a thalweg file name

    thalwegData_<centerOf>_<relId>.pickle (or extended_thalwegData_...) contains the release area id,
    thalwegData_<centerOf>_<startRow>_<startCol>.pickle does not

    Returns
    --------------
    relId: int or None
        release area id, None if the thalweg is defined by its start cell
    """
    stem = pathlib.Path(fileName).stem.removeprefix("extended_")
    nameParts = stem.split("_")
    if len(nameParts) == 3:
        return int(nameParts[2])
    return None


def getProfileInPath(pathOutput, profile, relId=None, pathPolygons=None):
    """
    get location and profile within the process path

    If the release area id (relId) and the process path polygons are available, the process path is the
    polygon of this release area. Otherwise all cells with flux > 0 (of all release areas) are used.
    The part of the profile within the process path is the continuous section from the first to the
    last point within the process path.

    Parameters
    --------------
    pathOutput: pathlib Path
        path to Output folder
    profile: dict
        contains profile parameters (x, y, z, s and optional zdelta), s is the horizontal
        distance along the profile points
    relId: int or None
        release area id of the thalweg
    pathPolygons: geopandas GeoDataFrame or None
        process path polygons (see getPathPolygons)

    Returns
    --------------
    profileInPath: dict
        contains profile parameters within the process path (s starts with 0); empty arrays if no
        point is within the process path
    indInpath: numpy array
        indices of the original profile that are within the process path
    """
    x = np.asarray(profile["x"], dtype=float)
    y = np.asarray(profile["y"], dtype=float)
    z = np.asarray(profile["z"], dtype=float)
    if "s" in profile:
        s = np.asarray(profile["s"], dtype=float)
    else:
        s = np.append([0], gT.computeLengthOfLine2D(x, y))

    indInPath = np.array([], dtype=int)
    processPath = None
    if relId is not None and pathPolygons is not None:
        processPath = pathPolygons.loc[pathPolygons["PRA_id"] == relId, "geometry"]
        if len(processPath) != 1:
            log.warning(
                f"{len(processPath)} process paths with id {relId} found, the flux raster is used instead."
            )
            processPath = None

    if processPath is not None:
        pointsThalweg = gpd.GeoSeries(gpd.points_from_xy(x, y))
        indCovered = np.where(pointsThalweg.covered_by(processPath.iloc[0]))[0]
        if indCovered.size > 0:
            indInPath = np.arange(indCovered[0], indCovered[-1] + 1)
    else:
        try:
            file = getRasterFile(pathOutput, variable="flux")
        except FileNotFoundError:
            file = getRasterFile(pathOutput, variable="cellCounts")
        fluxAlongThalweg = getThalwegValuesFromRaster(file, x, y)
        indFlux = np.where(fluxAlongThalweg > 0)[0]
        if indFlux.size > 0:
            # add the neighbouring points (the bilinear interpolation reduces the flux at the path border)
            indFirst = max(indFlux[0] - 1, 0)
            indLast = min(indFlux[-1] + 1, len(x) - 1)
            indInPath = np.arange(indFirst, indLast + 1)

    profileInPath = {
        "x": x[indInPath],
        "y": y[indInPath],
        "z": z[indInPath],
        "s": s[indInPath] - s[indInPath[0]] if indInPath.size > 0 else np.array([]),
    }
    if "zdelta" in profile:
        profileInPath["zdelta"] = np.asarray(profile["zdelta"], dtype=float)[indInPath]
    return profileInPath, indInPath


def saveExtPickle(profileExtended, inFileName):
    """
    save dictionary as pickle file, the filename is modified with an "extended"

    Parameters
    ----------
    profileExtended : dict
        dictionary that is saved
    inFileName : pathlib Path
        file name that is modified with an "extended"
    """
    outFileName = inFileName.parent / f"extended_{inFileName.stem}.pickle"

    with open(outFileName, "wb") as handle:
        pickle.dump(profileExtended, handle, protocol=pickle.HIGHEST_PROTOCOL)


# statistic variables (cfg statisticVariable) and the key of the effective values (see getEffectiveValues)
STATISTIC_VARIABLES = {
    "travelLengthMax": "travelLengthMax",
    "travelLengthAveraged": "travelLengthAveraged",
    "velocity": "velocityEff",
    "impressure": "impressureEff",
    "zdelta": "zdeltaEff",
    "zDelta": "zdeltaEff",
    # kept for compatibility: identical to velocity, impressure, zdelta
    "velocityAveraged": "velocityEff",
    "impressureAveraged": "impressureEff",
    "zdeltaAveraged": "zdeltaEff",
    # input parameters
    "alphaIn": "alphaIn",
    "velocityMaxIn": "velocityIn",
    "zdeltaMaxIn": "zDeltaIn",
}


def getDataBoxplots(path, variable, centerOf, rho=200, zDeltaType="averaged"):
    """
    get the data of one statistic variable for all thalwegs (one value per thalweg)

    Parameters:
    -----------
    path: pathlib Path
        OutputPath of the FlowPy simulation
    variable: str
        statistic variable (see STATISTIC_VARIABLES), relArea or the name of a result raster
        (e.g. flux, the maximum along the thalweg within the process path is used)
    centerOf: str
        center of variable
    rho: float
        snow density (default: 200) kg/m³
    zDeltaType: str
        type of simulated zDelta (zDeltaThalweg in the configuration)

    Returns:
    -----------
    data: numpy array
        value of the variable for all thalwegs (can contain nans)
    """
    if variable == "relArea":
        return getRelAreas(path)

    if variable in STATISTIC_VARIABLES:
        data = getEffectiveValues(path, centerOf, zDeltaType=zDeltaType, rho=rho)
        return data[STATISTIC_VARIABLES[variable]]

    # maximum of a result raster along the thalweg within the process path
    rasterFile = getRasterFile(path, variable=variable)
    values = []
    for thalweg in iterThalwegs(path, centerOf):
        valuesThalweg = getThalwegValuesFromRaster(
            rasterFile, thalweg["inPath"]["x"], thalweg["inPath"]["y"]
        )
        values.append(np.nanmax(valuesThalweg) if len(valuesThalweg) > 0 else np.nan)
    return np.array(values, dtype=float)


def iterThalwegs(path, centerOf):
    """
    iterate over all thalwegs (averaged and extended thalweg data) of one center of variable

    Parameters:
    -----------
    path: pathlib Path
        OutputPath of the FlowPy simulation
    centerOf: str
        center of variable

    Yields:
    -----------
    thalweg: dict
        name: name of the thalweg file (stem of the averaged thalweg file)
        relId: release area id (None if the thalweg is defined by its start cell)
        averaged: averaged thalweg data (one value per generation, saved by com4FlowPy)
        extended: extended thalweg data (one value per point of the extended thalweg)
        inPath: part of the extended thalweg within the process path (see getProfileInPath)
        indInPath: indices of the extended thalweg within the process path
    """
    pathPolygons = getPathPolygons(path)
    praIds = set(pathPolygons["PRA_id"]) if pathPolygons is not None else set()
    nFlux = 0
    for avgFile in sorted((path / "thalwegData").glob(f"thalwegData_{centerOf}_*.pickle")):
        extFile = avgFile.parent / f"extended_{avgFile.name}"
        if not extFile.is_file():
            log.warning(f"No extended thalweg found for {avgFile}, thalweg is skipped.")
            continue
        profileAveraged = np.load(avgFile, allow_pickle="TRUE")
        profileExtended = np.load(extFile, allow_pickle="TRUE")
        relId = getRelIdFromThalwegFile(avgFile.name)
        if relId is None or relId not in praIds:
            # no release area id or no process path polygon: the flux raster is used
            nFlux += 1
        profileInPath, indInPath = getProfileInPath(path, profileExtended, relId, pathPolygons)
        if indInPath.size == 0:
            log.warning(f"Thalweg {avgFile.stem} is not within its process path, thalweg is skipped.")
            continue
        yield {
            "name": avgFile.stem,
            "relId": relId,
            "averaged": profileAveraged,
            "extended": profileExtended,
            "inPath": profileInPath,
            "indInPath": indInPath,
        }
    if nFlux > 0:
        log.info(
            f"For {nFlux} thalwegs (no release area id or no process path polygon) the process path "
            "is taken from the flux raster (cells with flux > 0 of all release areas)."
        )


def getRelAreas(pathToOutput):
    """
    Read the release-area raster and return an array of all areas of release areas.

    Parameters
    ----------
    pathToOutput : str or pathlib.Path
        Path to the Outputs directory (or a subdirectory within it) of an
        avalanche project.

    Returns
    -------
    relAreas: numpy.ndarray
        One-dimensional array containing the area of each release area.
    """
    pathToOutput = pathlib.Path(pathToOutput)

    parts = pathToOutput.parts
    idx = parts.index("Outputs")
    pathToInputs = pathlib.Path(*parts[:idx]) / "Inputs"

    relIdPath = getRasterFile(pathToInputs / "RELID")
    relAreaPath = getRasterFile(pathToInputs / "RELArea")

    relIdDict = rasterUtils.readRaster(relIdPath)
    relAreaDict = rasterUtils.readRaster(relAreaPath)

    relIdRaster = relIdDict["rasterData"]
    relAreaRaster = relAreaDict["rasterData"]

    relIds, idx = np.unique(relIdRaster[relIdRaster > 0], return_index=True)
    relAreas = relAreaRaster[relIdRaster > 0][idx]

    return relAreas


# statistic variables that are derived from the simulated zDelta along the thalweg
SIMULATED_ZDELTA_VARIABLES = [
    "velocity",
    "impressure",
    "zDelta",
    "zdelta",
    "velocityAveraged",
    "zdeltaAveraged",
    "impressureAveraged",
]


def isSimulatedZDeltaVariable(variable):
    """True if the statistic variable is derived from the simulated zDelta along the thalweg"""
    return variable in SIMULATED_ZDELTA_VARIABLES


def getYlabelBoxplot(variable, zDeltaType=None):
    """
    return ylabel

    Parameters:
    --------------
    variable: str
        name of thalweg parameter that is plotted
    zDeltaType: str or None
        type of simulated zDelta (zDeltaThalweg in the configuration); if given, it is added to the label
        of variables derived from the simulated zDelta

    Returns:
    --------------
    ylabel: str
        ylabel for plot
    """

    if variable == "velocity":
        ylabel = "Max. Velocity [m/s]"
    elif variable == "impressure":
        ylabel = "Max. Impact pressure [kPa]"
    elif variable == "travelLengthMax":
        ylabel = "Runout length (horizontal) [m]"
    elif variable in ["zDelta", "zdelta"]:
        ylabel = "Max. zDelta [m]"
    elif variable == "flux":
        ylabel = "Max. flux"
    elif variable == "alphaIn":
        ylabel = "Input Alpha angle [°]"
    elif variable == "velocityMaxIn":
        ylabel = "Input Max. Velocity limit [m/s]"
    elif variable == "zdeltaMaxIn":
        ylabel = "Input Max. Velocity line height limit [m]"
    elif variable == "velocityAveraged":
        ylabel = "Max. Velocity [m/s]"
    elif variable == "zdeltaAveraged":
        ylabel = "Max. zDelta [m]"
    elif variable == "impressureAveraged":
        ylabel = "Max. Impact pressure [kPa]"
    elif variable == "travelLengthAveraged":
        ylabel = "Max. Travel length (FlowPy) [m]"
    elif variable == "relArea":
        ylabel = "Release area [m²]"
    else:
        message = f"{variable} is not a valid thalweg variable for the statistic boxplot"
        log.error(message)
        raise ValueError(message)
    if zDeltaType is not None and isSimulatedZDeltaVariable(variable):
        ylabel = f"{ylabel}\n(zDelta {getZDeltaLabel(zDeltaType)})"
    return ylabel


def logOverallStatistic(dataList, cfgSize, varLabel):
    """
    Computes and logs summary statistics (median, mean, 25th/75th percentile)
    over all data combined from every study area, and optionally logs the
    relative distribution of the data across predefined size classes.

    Parameters:
    -----------
    dataList: list of np.ndarray
        list containing one array of data values per study area. All arrays
        are concatenated into a single array before computing statistics.
    cfgSize: configparser SectionProxy
        configuration section containing the size class boundaries
    varLabel: str or None
        prefix used to look up the size class boundaries in cfgSize
        (e.g. "y" -> "ySize1Max"). If None, the size class distribution
        is skipped and only the overall statistics are logged.
    """
    dataAll = np.concatenate(dataList)
    log.info(f"Statistic of all {len(dataAll)} values:")

    log.info(f"Median: {np.median(dataAll)}")
    log.info(f"Mean: {np.mean(dataAll)}")
    log.info(f"25% percentile: {np.percentile(dataAll, 25)}")
    log.info(f"75% percentile: {np.percentile(dataAll, 75)}")

    # Distribution in classes
    if varLabel is not None:
        ysize1Max = cfgSize.getint(f"{varLabel}Size1Max")
        ysize2Max = cfgSize.getint(f"{varLabel}Size2Max")
        ysize3Max = cfgSize.getint(f"{varLabel}Size3Max")
        ysize4Max = cfgSize.getint(f"{varLabel}Size4Max")

        dataLen = len(dataAll)
        lenSize0 = np.sum((dataAll == 0))
        lenSize1 = np.sum((dataAll > 0) & (dataAll < ysize1Max))
        lenSize2 = np.sum((dataAll >= ysize1Max) & (dataAll < ysize2Max))
        lenSize3 = np.sum((dataAll >= ysize2Max) & (dataAll < ysize3Max))
        lenSize4 = np.sum((dataAll >= ysize3Max) & (dataAll < ysize4Max))
        lenSize5 = np.sum((dataAll >= ysize4Max))

        log.info(f"Relative Part in size 1: {lenSize1 / dataLen}")
        log.info(f"Relative Part in size 2: {lenSize2 / dataLen}")
        log.info(f"Relative Part in size 3: {lenSize3 / dataLen}")
        log.info(f"Relative Part in size 4: {lenSize4 / dataLen}")
        log.info(f"Relative Part in size 5: {lenSize5 / dataLen}")
        log.info(f"Relative Part in size 0: {lenSize0 / dataLen}")

        for i, data in enumerate(dataList):
            dataLen = len(data)
            lenSize0 = np.sum((data == 0))
            lenSize1 = np.sum((data > 0) & (data < ysize1Max))
            lenSize2 = np.sum((data >= ysize1Max) & (data < ysize2Max))
            lenSize3 = np.sum((data >= ysize2Max) & (data < ysize3Max))
            lenSize4 = np.sum((data >= ysize3Max) & (data < ysize4Max))
            lenSize5 = np.sum((data >= ysize4Max))

            log.info(f"Study area {i}, Relative Part in size 1: {lenSize1 / dataLen}")
            log.info(f"Study area {i}, Relative Part in size 2: {lenSize2 / dataLen}")
            log.info(f"Study area {i}, Relative Part in size 3: {lenSize3 / dataLen}")
            log.info(f"Study area {i}, Relative Part in size 4: {lenSize4 / dataLen}")
            log.info(f"Study area {i}, Relative Part in size 5: {lenSize5 / dataLen}")
            log.info(f"Study area {i}, Relative Part in size 0: {lenSize0 / dataLen}")


def computeRunoutAngle(z, s):
    """
    compute the runout angle between the first (top) and the last (end of runout)
    point of a thalweg profile

    Parameters
    -----------
    z: numpy array
        altitude along the thalweg [m]
    s: numpy array
        travel length along the thalweg [m]

    Returns
    -----------
    alpha: float
        runout angle [°], nan if the profile is empty or has no horizontal length
    """
    z = np.asarray(z, dtype=float)
    s = np.asarray(s, dtype=float)
    if z.size == 0 or s.size == 0:
        return np.nan

    deltaZ = z[0] - z[-1]
    deltaS = s[-1] - s[0]
    if deltaS <= 0:
        return np.nan
    alpha = np.rad2deg(np.arctan(deltaZ / deltaS))

    return alpha


def getReleaseAreaTops(relIdFile, demFile):
    """
    get the highest point (DEM cell) of every release area

    Parameters
    -----------
    relIdFile: pathlib Path
        raster file with the release area id in every release cell
    demFile: pathlib Path
        DEM raster file (same grid as relIdFile)

    Returns
    -----------
    releaseTops: dict
        release area id: (x, y, z) of its highest cell
    """
    relIdDict = rasterUtils.readRaster(relIdFile)
    demDict = rasterUtils.readRaster(demFile)
    header = relIdDict["header"]
    relIds = relIdDict["rasterData"]
    dem = demDict["rasterData"]
    if relIds.shape != dem.shape:
        message = f"Release id raster {relIdFile} and DEM {demFile} do not have the same grid."
        log.error(message)
        raise ValueError(message)

    rows, cols = np.where(relIds > 0)
    ids = relIds[rows, cols].astype(int)
    z = dem[rows, cols]
    # sort by id and descending altitude, the first cell of each id is its highest cell
    order = np.lexsort((-z, ids))
    _, indFirst = np.unique(ids[order], return_index=True)
    indTop = order[indFirst]

    x = header["xllcenter"] + cols[indTop] * header["cellsize"]
    y = header["yllcenter"] + rows[indTop] * header["cellsize"]
    releaseTops = {
        relId: (xTop, yTop, zTop) for relId, xTop, yTop, zTop in zip(ids[indTop], x, y, z[indTop])
    }
    return releaseTops


def getEffectiveValues(path, centerOf, zDeltaType="averaged", rho=200):
    """
    get input and effective values of every thalweg (one definition for all statistic plots)

    Definitions:
    - process path: polygon of the release area (pathPolygons), if not available: cells with flux > 0
    - s: horizontal distance along the thalweg points
    - effective zDelta: maximum of the simulated zDelta (zDeltaType) along the averaged thalweg

    Parameters
    -----------
    path: pathlib Path
        Thalweg-Output Path of the FlowPy simulation
    centerOf: str
        center of variable
    zDeltaType: str
        type of simulated zDelta (zDeltaThalweg in the configuration)
    rho: float
        snow density (for the impact pressure) [kg/m³]

    Returns
    -----------
    data: dict
        contains numpy arrays (one value per thalweg, same order for all keys) and the list "name":
        alphaIn: input alpha angle [°]
        zDeltaIn: input zDelta maximum [m]
        velocityIn: input (model parameter) max. velocity [m/s]
        zdeltaEff: effective max. zDelta along the averaged thalweg [m]
        velocityEff: effective max. velocity along the averaged thalweg [m/s]
        impressureEff: effective max. impact pressure along the averaged thalweg [kPa]
        travelLengthMax: horizontal distance from the first to the last point of the extended
        thalweg within the process path [m]
        travelLengthAveraged: maximum travel length of FlowPy ("travelLength" of the averaged thalweg) [m]
        alphaEff: effective runout angle [°] along the extended thalweg, from its first to its last
        point within the process path (same section as travelLengthMax, see computeRunoutAngle)
        alphaEffRelTop: as alphaEff, but starting at the highest point of the release area (its s is
        taken from the nearest point of the extended thalweg)
        alphaEffAveraged: runout angle [°] of the averaged (not extended) thalweg from its first to its
        last point, z from the DEM at the averaged x, y and s along the averaged x, y
        gammaEnd: averaged travel angle [°] ("gamma" in the averaged thalweg file) of the last generation,
        nan if the thalweg file contains no gamma
    """
    keys = [
        "alphaIn",
        "zDeltaIn",
        "velocityIn",
        "zdeltaEff",
        "velocityEff",
        "impressureEff",
        "travelLengthMax",
        "travelLengthAveraged",
        "alphaEff",
        "alphaEffRelTop",
        "alphaEffAveraged",
        "gammaEnd",
    ]
    data = {key: [] for key in keys}
    data["name"] = []

    avaDir = pathlib.Path(*path.parts[: path.parts.index("Outputs")])
    demFile = gI.getDEMPath(avaDir)
    try:
        releaseTops = getReleaseAreaTops(getRasterFile(avaDir / "Inputs" / "RELID"), demFile)
    except FileNotFoundError:
        log.info("No release area id raster found, alphaEffRelTop is not computed.")
        releaseTops = {}

    for thalweg in iterThalwegs(path, centerOf):
        profile = thalweg["extended"]
        profileAveraged = thalweg["averaged"]
        relId = thalweg["relId"]
        indStart = thalweg["indInPath"][0]
        indEnd = thalweg["indInPath"][-1]

        # input parameters
        zDeltaIn = getMaxZDeltaInput(profileAveraged)
        data["alphaIn"].append(profileAveraged["alpha"])
        data["zDeltaIn"].append(zDeltaIn)
        data["velocityIn"].append(zDelta2velocity(zDeltaIn))

        # effective zDelta, velocity and impact pressure along the averaged thalweg
        zDeltaAveraged = getSimulatedZDeltaAveraged(profileAveraged, zDeltaType, path)
        if zDeltaAveraged.size > 0 and not np.all(np.isnan(zDeltaAveraged)):
            zdeltaEff = np.nanmax(zDeltaAveraged)
        else:
            zdeltaEff = np.nan
        velocityEff = zDelta2velocity(zdeltaEff)
        data["zdeltaEff"].append(zdeltaEff)
        data["velocityEff"].append(velocityEff)
        data["impressureEff"].append(velocity2pressure(velocityEff, rho))

        # runout (horizontal distance) and travel length (FlowPy)
        data["travelLengthMax"].append(thalweg["inPath"]["s"][-1])
        travelLength = np.asarray(profileAveraged.get("travelLength", []), dtype=float)
        data["travelLengthAveraged"].append(np.nanmax(travelLength) if travelLength.size > 0 else np.nan)

        # effective runout angle along the extended thalweg within the process path (first to last point)
        data["alphaEff"].append(
            computeRunoutAngle(profile["z"][indStart : indEnd + 1], profile["s"][indStart : indEnd + 1])
        )

        # alternative start: highest point of the release area, its s is taken from the nearest thalweg point
        if relId is not None and relId in releaseTops:
            xTop, yTop, zTop = releaseTops[relId]
            indTop = np.argmin(np.hypot(profile["x"] - xTop, profile["y"] - yTop))
            alphaEffRelTop = computeRunoutAngle([zTop, profile["z"][indEnd]], profile["s"][[indTop, indEnd]])
        else:
            alphaEffRelTop = np.nan
        data["alphaEffRelTop"].append(alphaEffRelTop)

        # runout angle of the averaged (not extended) thalweg, from its first to its last point:
        # z is read from the DEM at the averaged x, y and s is the horizontal distance along the averaged x, y
        xAvg = np.asarray(profileAveraged["x"], dtype=float)
        yAvg = np.asarray(profileAveraged["y"], dtype=float)
        if xAvg.size > 1:
            zAvg = getThalwegValuesFromRaster(demFile, xAvg, yAvg)
            sAvg = np.append([0], gT.computeLengthOfLine2D(xAvg, yAvg))
            data["alphaEffAveraged"].append(computeRunoutAngle(zAvg, sAvg))
        else:
            data["alphaEffAveraged"].append(np.nan)

        # averaged travel angle (com4FlowPy max_gamma) of the last generation, i.e. at the runout end
        gammaAvg = np.asarray(profileAveraged.get("gamma", []), dtype=float)
        data["gammaEnd"].append(gammaAvg[-1] if gammaAvg.size > 0 else np.nan)

        data["name"].append(thalweg["name"])

    for key in keys:
        data[key] = np.array(data[key], dtype=float)

    return data
