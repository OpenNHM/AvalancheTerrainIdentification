"""
Tools/ help functions for regional thalweg plots
"""

import numpy as np
import pathlib
import rasterio
import logging
import os
import pickle
import copy

import avaframe.in2Trans.rasterUtils as rasterUtils
import avaframe.in3Utils.geoTrans as gT

# create local logger
log = logging.getLogger("avaframe.modules.regionalThalwegTools")


def searchResFolder(avalanchedir, module="com4FlowPy"):
    dir = avalanchedir / "Outputs" / module / "peakFiles"

    resFolders = []
    for filename in os.listdir(dir):
        if filename.startswith("res_"):
            resFolders.append(filename)
    if len(resFolders) == 0:
        message = f"No results {module} folder found in {dir}"
        log.error(message)
        raise FileNotFoundError(message)
    elif len(resFolders) > 1:
        oneResFolder = False
        simHash = ""
    elif len(resFolders) == 1:
        oneResFolder = True
        print(str(resFolders[0]).split("res_", 1))
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

    try:
        raster = rasterio.open(path)
        filePath = path
    except:
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
    """
    centerOf = titleDict["centerOf"]
    startRow = titleDict["startRow"]
    startCol = titleDict["startCol"]
    relId = titleDict["relId"]

    if startRow != "":
        filePath = pathlib.Path(f"{path}/thalwegData_{centerOf}_{startRow}_{startCol}.pickle")
    else:
        filePath = pathlib.Path(path) / (f"thalwegData_{centerOf}_{relId}.pickle")
    if filePath.is_file():
        data = np.load(filePath, allow_pickle="TRUE")
    else:
        message = f"No thalwegdata exist averaged with {centerOf} for starcell with row {startRow} and column {startCol} in {path}"
        log.error(message)
        raise FileNotFoundError(message)
    return data


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
        Index after the last point in extendedProfile for which interpolation
        is performed. If None, interpolation is performed until the end of
        the profile.

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
        indEnd = len(sExt)

    # Allocate output and fill with boundary values
    varExt = np.full(len(sExt), endValue, dtype=float)
    varExt[:indStart] = startValue

    # Interpolate only on the requested section
    sExtShort = sExt[indStart:indEnd]
    if len(sExtShort) >= 1:
        sExtShort = sExtShort - sExtShort[0]

    if len(sAvg) > 1:
        varExt[indStart:indEnd] = np.interp(
            sExtShort,
            sAvg,
            varAvg,
            left=startValue,
            right=endValue,
        )

    extendedProfile[variable] = varExt

    return extendedProfile


def getThalwegValuesFromRaster(rasterFile, x, y):
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
    )
    return thalwegValues


def getProfileInPath(pathOutput, profile):
    """
    get location and profile within the flow path

    Parameters
    --------------
    pathOutput: pathlib Path
        path to Output folder
    profile: dict
        contains profile parameters

    Returns
    --------------
    profileInPath: dict
        contains profile parameters within the flow path
    indInpath: numpy array
        indices of the original profile that are within the flow path

    """
    x = profile["x"]
    y = profile["y"]
    z = profile["z"]
    try:
        file = getRasterFile(pathOutput, variable="flux")
    except:
        file = getRasterFile(pathOutput, variable="cellCounts")
    fluxAlongThalweg = getThalwegValuesFromRaster(file, x, y)

    # only use these values that are within the avalanche path
    # and add those values from the corner
    indInPath = np.where(fluxAlongThalweg > 0)[0]
    if indInPath.size > 0:
        if indInPath[0] > 0:
            indInPath = np.append(indInPath[0] - 1, indInPath)
        if (indInPath[-1] + 1) < len(fluxAlongThalweg):
            indInPath = np.append(indInPath, indInPath[-1] + 1)

        x = x[indInPath]
        y = y[indInPath]
        s = np.append([0], gT.computeLengthOfLine2D(x, y))
        z = z[indInPath]

        profileInPath = {"x": x, "y": y, "s": s, "z": z}

        if "zdelta" in profile:
            zdelta = profile["zdelta"][indInPath]
            profileInPath["zdelta"] = zdelta

    else:
        profileInPath = copy.deepcopy(profile)
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
    dir = inFileName.parent
    fileName = inFileName.stem
    outFileName = dir / f"extended_{fileName}.pickle"

    with open(outFileName, "wb") as handle:
        pickle.dump(profileExtended, handle, protocol=pickle.HIGHEST_PROTOCOL)


def getDataBoxplots(path, variable, centerOf, rho=200):
    """
    get the thalweg data

    Parameters:
    -----------
    path: pathlib Path
        OutputPath of the FlowPy simulation
    variable: str
        name of output variable that is analysed and plotted (e.g, impressure, travelLengthMax)
    rho: float
        snow density (default: 200) kg/m³

    Returns:
    -----------
    data: numpy array
        maximum value of the parameter varName of all thalwegs
    """

    data = ""

    if "velocity" in variable:
        varName = "velocity"
        variable = variable.replace("velocity", "zdelta")

    elif "impressure" in variable:
        varName = "impressure"
        variable = variable.replace("impressure", "zdelta")
    else:
        varName = f"{variable}"

    if variable == "relArea":
        releaseAreas = getRelAreas(path)
        return releaseAreas

    dataDict = maxParameterOfAllThalwegs(path, variable, centerOf)
    data = np.array(dataDict[variable])
    if "velocity" in varName:
        data = zDelta2velocity(data)

    if "impressure" in varName:
        velo = zDelta2velocity(data)
        data = velocity2pressure(velo, rho)

    return data


def maxParameterOfAllThalwegs(path, variableList, centerOf):
    """
    get thalweg data (maximum per thalweg)

    Parameters:
    -----------
    path: pathlib Path
        Thalweg-Output Path of the FlowPy simulation
    variable: str
        name of thalweg parameter
    centerOf: str
        center of variable

    Returns:
    -----------
    variableValues: list
        maximum values of the parameter variable of all thalwegs
    """
    if type(variableList) == str:
        variableList = [variableList]
    variableValues = {}
    for variable in variableList:
        variableValues[variable] = []
        variableValues["velocity"] = []
        variableValues["velocityIn"] = []
        for filename in os.listdir(path / "thalwegData"):
            # Check if the filename starts with 'thalweg'
            if filename.startswith(f"extended_thalwegData_{centerOf}"):
                # Construct full file path
                filePath = path / "thalwegData" / filename
                data = np.load(filePath, allow_pickle="TRUE")
                profileInPath, _ = getProfileInPath(path, data)
                x = profileInPath["x"]
                y = profileInPath["y"]

                if variable == "alphaIn":
                    alpha = data["alpha"]
                    variableValues[variable].append(alpha)
                elif variable == "zdeltaMaxIn":
                    zDelta = data["zDeltaMax"]
                    variableValues[variable].append(zDelta)
                elif variable == "travelLengthMax":
                    variableValues[variable].append(profileInPath["s"][-1])
                elif "Averaged" in variable:

                    values = data[variable.replace("Averaged", "")]
                    if len(values) > 0:
                        variableValues[variable].append(np.nanmax(values))
                    else:
                        variableValues[variable].append(np.nan)
                elif "zdelta" in variable:
                    maxZdelta = np.nanmax(profileInPath["zdelta"])
                    variableValues[variable].append(maxZdelta)
                elif variable == "test":
                    # TODO: rename test!
                    zDelta = data["zDeltaMax"]
                    velocity = zDelta2velocity(zDelta)
                    variableValues["velocityIn"].append(velocity)

                    zThalweg = data["zdelta"]
                    velThalweg = zDelta2velocity(zThalweg)
                    if len(zThalweg) > 0:
                        variableValues["velocity"].append(np.nanmax(velThalweg))
                    else:
                        variableValues["velocity"].append(np.nan)
                else:
                    outputRasterFile = getRasterFile(path, variable=variable)
                    valuesThalweg = getThalwegValuesFromRaster(outputRasterFile, x, y)
                    if len(valuesThalweg) > 0:
                        valueMax = np.nanmax(valuesThalweg)
                    else:
                        valueMax = np.nan
                    variableValues[variable].append(valueMax)

                    # for plotting averaged values:
                    # variableValues[variable].append(np.nanmax(data[variable]))
    return variableValues


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


def getYlabelBoxplot(variable):
    """
    return ylabel

    Parameters:
    --------------
    variable: str
        name of thalweg parameter that is plotted

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
        ylabel = "Runout length [m]"
    elif variable == "zDelta":
        ylabel = "Max. zDelta [m]"
    elif variable == "flux":
        ylabel = "Flux"
    elif variable == "alphaIn":
        ylabel = "Input Alpha angle [°]"
    elif variable == "velocityMaxIn":
        ylabel = "Input Max. Velocity limit [m/s]"
    elif variable == "zdeltaMaxIn":
        ylabel = "Input Max. Velocity line height limit [m]"
    elif variable == "velocityAveraged":
        ylabel = "Max. Velocity averaged [m/s]"
    elif variable == "zdeltaAveraged":
        ylabel = "Max. Velocity line height averaged [m]"
    elif variable == "impressureAveraged":
        ylabel = "Max. Impact pressure averaged [kPa]"
    elif variable == "travelLengthAveraged":
        ylabel = "Max. Travel length averaged [m]"
    elif variable == "relArea":
        ylabel = "Release area [m²]"
    else:
        message = f"{variable} is not a valid thalweg variable for the statistic boxplot"
        log.error(message)
        raise ValueError(message)
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

    print(dataAll.shape)

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
        lenSize1 = np.sum((dataAll >= 0) & (dataAll < ysize1Max))
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
            lenSize1 = np.sum((data >= 0) & (data < ysize1Max))
            lenSize2 = np.sum((data >= ysize1Max) & (data < ysize2Max))
            lenSize3 = np.sum((data >= ysize2Max) & (data < ysize3Max))
            lenSize4 = np.sum((data >= ysize3Max) & (data < ysize4Max))
            lenSize5 = np.sum((data >= ysize4Max))

            log.info(f"Study area {i}, Relative Part in size 1: {lenSize1 / dataLen}")
            log.info(f"Study area {i},Relative Part in size 2: {lenSize2 / dataLen}")
            log.info(f"Study area {i},Relative Part in size 3: {lenSize3 / dataLen}")
            log.info(f"Study area {i},Relative Part in size 4: {lenSize4 / dataLen}")
            log.info(f"Study area {i},Relative Part in size 5: {lenSize5 / dataLen}")
            log.info(f"Study area {i},Relative Part in size 0: {lenSize0 / dataLen}")


def getEffectiveVsInputData(path, centerOf):
    """
    get paired input vs. effective values (runout angle and velocity) for every
    thalweg, so they can be used for a scatter/regression plot

    Parameters
    -----------
    path: pathlib Path
        Thalweg-Output Path of the FlowPy simulation
    centerOf: str
        center of variable

    Returns
    -----------
    data: dict
        contains numpy arrays (one value per thalweg, same order for all keys):
        alphaIn: input alpha angle [°]
        alphaEff: effective runout angle [°]
        velocityIn: input (model parameter) max. velocity [m/s]
        velocityEff: effective max. velocity along the thalweg [m/s]
    """
    data = {"alphaIn": [], "alphaEff": [], "velocityIn": [], "velocityEff": []}

    for filename in os.listdir(path / "thalwegData"):
        if filename.startswith(f"extended_thalwegData_{centerOf}"):
            filePath = path / "thalwegData" / filename
            profile = np.load(filePath, allow_pickle="TRUE")
            profileInPath, indInPath = getProfileInPath(path, profile)

            if indInPath.size == 0 or "zdelta" not in profileInPath:
                continue

            z = profile["z"]
            s = profile["s"]
            zdelta = profile["zdelta"]

            """

            maskNan = np.ones(zdelta.shape, dtype=bool)
            maskNan[indInPath] = False
            zdelta[maskNan] = np.nan
            s[maskNan] = np.nan
            z[maskNan] = np.nan
            """

            # calculate effective runout angle
            angle_rad = np.arctan((np.nanmax(z) - np.nanmin(z)) / (np.nanmax(s) - np.nanmin(s)))
            angle_degrees = np.rad2deg(angle_rad)

            if len(zdelta) == 0 or np.all(np.isnan(zdelta)):
                continue

            angleRad = np.arctan((np.nanmax(z) - np.nanmin(z)) / (np.nanmax(s) - np.nanmin(s)))
            alphaEff = np.rad2deg(angleRad)

            velocityIn = zDelta2velocity(profile["zDeltaMax"])
            velocityEff = zDelta2velocity(np.nanmax(zdelta))

            data["alphaIn"].append(profile["alpha"])
            data["alphaEff"].append(angle_degrees)
            data["velocityIn"].append(velocityIn)
            data["velocityEff"].append(velocityEff)

    for key in data:
        data[key] = np.array(data[key], dtype=float)

    return data
