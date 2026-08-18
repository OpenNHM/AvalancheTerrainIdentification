import numpy as np
import pathlib
import matplotlib.pyplot as plt
import logging
import copy

import modules.mod3Map.regionalThalwegTools as tools
import modules.mod3Map.regionalThalwegPlotTools as plotTools
import modules.mod0Helper.helpFunctions as helper

from avaframe.in3Utils import cfgHandling
from avaframe.in3Utils import fileHandlerUtils as fU
import avaframe.out3Plot.outAIMEC as outAIMEC
from avaframe.in3Utils import cfgUtils
from avaframe.ana3AIMEC import ana3AIMEC
import avaframe.ana5Utils.preparePathGeneral as pathGen
import avaframe.in1Data.getInput as gI
from avaframe.ana5Utils import DFAPathGeneration
import avaframe.in2Trans.rasterUtils as rasterUtils
from avaframe.out3Plot import outCom3Plots

log = logging.getLogger("avaframe.modules.regionalThalwegAnalysis")


def regionalThalweg2DPlotMain(avalanchedir, cfg, simhash="", studyAreaName=None):
    """
    read in Input data and general function for 2D thalweg plot

    Parameters
    -----------
    avalanchedir: str
        Path to the th avalanche directory
    cfg: configparser Object
        contains configuration settings
    """
    avalanchedir = pathlib.Path(avalanchedir)

    cfgDFAPath = cfgUtils.getModuleConfig(
        DFAPathGeneration,
        onlyDefault=cfg["ana5Utils_DFAPathGeneration_override"].getboolean("defaultConfig"),
    )
    # and override with settings from config
    cfgDFAPath, cfg = cfgHandling.applyCfgOverride(cfgDFAPath, cfg, DFAPathGeneration, addModValues=False)

    module = cfg["GENERAL"].get("modName")
    startRow = cfg["GENERAL"].get("startRow")
    startCol = cfg["GENERAL"].get("startCol")
    relId = cfg["GENERAL"].get("relId")
    cfgFlags = cfg["FLAGS"]

    if simhash == "":
        _, simhash = tools.searchResFolder(avalanchedir, module)
        if simhash == "":
            simhash = cfg["GENERAL"].get("simHash")
            if simhash == "":
                message = "If there are multiple results folder, choose the simhash that is analysed."
                log.error(message)
                raise ValueError(message)
    else:
        cfg["GENERAL"]["simHash"] = simhash

    pathToOutput = avalanchedir / "Outputs" / module / "peakFiles" / f"res_{simhash}"
    savePath = avalanchedir / "Outputs" / "regionalThalwegPlot"
    fU.makeADir(savePath)
    pathDict = {"avalancheDir": avalanchedir, "pathToOutput": pathToOutput, "savePath": savePath}
    if studyAreaName is not None:
        pathDict["studyAreaName"] = studyAreaName

    demDict = gI.readDEM(avalanchedir)
    # TODO: Check if flipping DEM is needed!(gI.readDem flips the raster.)
    # demDict["rasterData"] = np.flipud(demDict["rasterData"])

    # check which thalweg is plotted
    if startRow != "" and startCol != "" and relId != "":
        message = "When choosing one thalweg that is plotted, only select with startcell coordinates or release Id!"
        log.error(message)
        raise ValueError(message)
    plotAllThalwegs = False
    if startCol != "" or startRow != "":
        startCol = np.int16(startCol)
        startRow = np.int16(startRow)
    elif relId != "":
        relId = np.int32(relId)
    else:
        plotAllThalwegs = True

    centerOf = cfg["GENERAL"].get("centerOfVariable")
    if centerOf == "":
        plotAllCenterOf = True
    else:
        plotAllCenterOf = False

    pathDict["titleVariables"] = {
        "startRow": startRow,
        "startCol": startCol,
        "relId": relId,
        "centerOf": centerOf,
        "simHash": simhash,
    }

    # read in thalweg data
    if plotAllCenterOf:
        log.info(f"Plot all thalweg data that can be found in {pathToOutput}/ThalwegData.")
        files = sorted(list((pathToOutput / "thalwegData").glob(f"thalwegData_*.pickle")))
    elif plotAllThalwegs:
        log.info(
            f"Plot all thalwegs averaged with {centerOf} that can be found in {pathToOutput}/ThalwegData."
        )
        files = sorted(list((pathToOutput / "thalwegData").glob(f"thalwegData_{centerOf}_*.pickle")))
        if len(files) == 0:
            message = f"There is no thalweg data computed with {centerOf} in {pathToOutput}/ThalwegData."
            log.error(message)
            raise FileNotFoundError(message)
    fileDict = {}
    if plotAllThalwegs or plotAllCenterOf:
        for thalwegDataFile in files:
            stem = thalwegDataFile.stem
            nameParts = stem.split("_")
            if len(nameParts) == 4:
                _, centerOf, startRow, startCol = stem.split("_")
            elif len(nameParts) == 3:
                _, centerOf, relId = stem.split("_")
            pathDictLoop = copy.deepcopy(pathDict)

            pathDictLoop["titleVariables"]["startRow"] = startRow
            pathDictLoop["titleVariables"]["startCol"] = startCol
            pathDictLoop["titleVariables"]["centerOf"] = centerOf
            pathDictLoop["titleVariables"]["relId"] = relId

            dataThalweg = np.load(thalwegDataFile, allow_pickle="TRUE")

            if "zDelta" in dataThalweg and "zdelta" not in dataThalweg:
                dataThalweg["zdelta"] = dataThalweg["zDelta"]

            _, profileExtended = pathGen.preparePathGeneralMain(dataThalweg, cfgDFAPath, demDict)

            if cfg["GENERAL"].getboolean("averagedZdelta"):
                profileExtended = tools.interpolateValueFromAveragedToExtended(dataThalweg, profileExtended,
                                                                               "zdelta", startValue=0,
                                                                               endValue=0,
                                                                               indStart=profileExtended[
                                                                                   "indStartMassAverage"],
                                                                               indEnd=profileExtended[
                                                                                   "indEndMassAverage"])
            else:
                zDeltaRasterFile = tools.getRasterFile(pathDict["pathToOutput"], variable="zdelta")

                profileExtended["zdelta"] = tools.getThalwegValuesFromRaster(
                    zDeltaRasterFile, profileExtended["x"], profileExtended["y"]
                )

            fileDict[thalwegDataFile] = {"pathDict": pathDictLoop, "thalwegData": profileExtended,
                                         "thalwegDataAveraged": dataThalweg
                                         }
            tools.saveExtPickle(profileExtended, thalwegDataFile)
    else:
        thalwegDataFile = pathToOutput / "thalwegData"
        dataThalweg = tools.readThalwegData(thalwegDataFile, pathDict["titleVariables"])
        _, profileExtended = pathGen.preparePathGeneralMain(dataThalweg, cfgDFAPath, demDict)

        if cfg["GENERAL"].getboolean("averagedZdelta"):
            profileExtended = tools.interpolateValueFromAveragedToExtended(dataThalweg, profileExtended,
                                                                           "zdelta", startValue=0,
                                                                           endValue=0,
                                                                           indStart=profileExtended[
                                                                               "indStartMassAverage"],
                                                                           indEnd=profileExtended[
                                                                               "indEndMassAverage"])
        else:
            zDeltaRasterFile = tools.getRasterFile(pathDict["pathToOutput"], variable="zdelta")

            profileExtended["zdelta"] = tools.getThalwegValuesFromRaster(
                zDeltaRasterFile, profileExtended["x"], profileExtended["y"]
            )

        tools.saveExtPickle(profileExtended, thalwegDataFile)
        fileDict[thalwegDataFile] = {"pathDict": pathDict, "thalwegData": profileExtended,
                                     "thalwegDataAveraged": dataThalweg
                                     }

    # make plots
    for fileName in fileDict.keys():
        profileExtended = fileDict[fileName]["thalwegData"]
        pathDict = fileDict[fileName]["pathDict"]

        # derive zdelta value along path

        if cfgFlags.getboolean("plotThalweg2D"):
            plotThalweg2D(pathDict, cfg, profileExtended)
        if cfgFlags.getboolean("plotThalwegAltitude"):
            plotDFAThalwegAltitude(pathDict, profileExtended)
        if cfgFlags.getboolean("plotThalwegLocation"):
            plotDFAGenerationLocation(cfg, pathDict, profileExtended, rasterVariable="fpTravelAngleMax")
    if cfgFlags.getboolean("plotAllThalwegLocations"):
        plotThalweg2D(pathDict, cfg, profileExtended, onlyField=True)
    if cfgFlags.getboolean("plotStatisticBoxplot"):
        plotTools.plotBoxplot(pathDict, cfg)
    if cfgFlags.getboolean("plotStatisticScatterPlot"):
        plotTools.plotScatterInputEffective(pathDict, cfg)

    return pathDict


def plotThalweg2D(pathDict, cfg, dataThalweg, onlyField=False):
    """
    saves 2D thalweg plot:
    top panel: position of the thalweg in the field
    bottom panel: 2 dimensional representation

    Parameters
    ------------
    pathDict: dict
        contains the simulation paths
    cfg: configparser Object
        contains configuration settings
    dataThalweg: numpy array
        thalweg data that are saved in the simulation (averaged x-, y-coordinates, zdelta, ..)
    onlyField: bool
        if True: only the field with thalweg locations is plotted

    """
    variable = cfg["GENERAL"].get("plotVariable")
    thalwegPra = cfg["GENERAL"].getboolean("thalwegPra")
    size = cfg["GENERAL"].get("avalancheSize")
    savePath = pathDict["savePath"]
    centerOf = pathDict["titleVariables"]["centerOf"]

    if thalwegPra:
        folder = pathlib.Path(pathDict["pathToOutput"] / "thalwegData")
        # choose if we represent the thalweg that is averaged or extended
        if cfg["GENERAL"].getboolean("2DExtendedThalwegs"):
            files = list(folder.glob(f"extended_thalwegData_{centerOf}*"))
        else:
            files = list(folder.glob(f"thalwegData_{centerOf}*"))
        x = []
        y = []

        for thalwegFile in files:
            data = np.load(thalwegFile, allow_pickle="TRUE")
            newX = np.array(data["x"])
            newY = np.array(data["y"])

            y.append(newY)
            x.append(newX)
    else:
        y = np.array(dataThalweg[f"y"])
        x = np.array(dataThalweg[f"x"])

    # PLOT
    if onlyField:
        fig, ax = plt.subplots(figsize=(10, 8))
        fig, ax = plotTools.makeFieldPlot(ax, fig, cfg, pathDict, x, y, dataThalweg)
    else:
        fig, axs = plt.subplots(2, 1)

        fig.set_figheight(10)
        fig.tight_layout(pad=3.0)
        fig.set_figwidth(8)

        fig, axs[0] = plotTools.makeFieldPlot(axs[0], fig, cfg, pathDict, x, y, dataThalweg)
        axs[1] = plotTools.makeThalwegPlot(
            axs[1], dataThalweg, pathDict, colorPra=cfg["GENERAL"].get("colorPra")
        )

    outFileNamePart = tools.getOutFileNamePartly(pathDict["titleVariables"], allThalwegs=onlyField)
    outFileName = f"Thalweg2D_{outFileNamePart}.png"
    fig.savefig(savePath / outFileName)
    log.info(f"saved plot: {(savePath / outFileName)}")


def plotDFAGenerationLocation(cfg, pathDict, profile, rasterVariable="fpTravelAngleMax"):
    savePath = pathDict["savePath"]
    colorPra = cfg["GENERAL"].get("colorPra")
    # TODO: putplotLim into cfg
    plotLim = 100

    if rasterVariable == "velocityMax":
        rasterFileVariable = "zdelta"
    else:
        rasterFileVariable = rasterVariable

    file = tools.getRasterFile(pathDict["pathToOutput"], variable=rasterFileVariable)
    rasterDict = rasterUtils.readRaster(file)
    raster = rasterDict["rasterData"]
    raster = np.where(raster > 0, raster, 0)
    if rasterVariable == "velocityMax":
        raster = helper.zDelta2velocity(raster)

    dem = gI.readDEM(pathDict["avalancheDir"])

    fig, ax1 = plt.subplots(figsize=(8, 15))  # figsize=(12, 9))  # , dpi=150)
    ax1 = outCom3Plots.avalancheThalwegPlot(ax1, raster, dem, profile, cmapHS="gray")
    ax1.legend()

    plotTools.addReleaseAreaToPlot(ax1, pathDict, f"#{colorPra}", linewidth=2)

    # set plot limits depending on thalweg
    plt.xlim((np.min(profile["x"]) - plotLim, np.max(profile["x"]) + plotLim))
    plt.ylim((np.min(profile["y"]) - plotLim, np.max(profile["y"]) + plotLim))

    outFileNamePart = tools.getOutFileNamePartly(pathDict["titleVariables"])
    outFileName = f"DFA_thalwegLocation_{outFileNamePart}.png"

    fig.savefig(savePath / outFileName)
    log.info(f"saved plot: {(savePath / outFileName)}")


def plotDFAThalwegAltitude(pathDict, dataThalweg):
    """
    plot the AIMEC thalweg-altitude plot

    Parameters
    """
    dataThalweg["indStartOfRunout"] = 0
    dataThalweg["startOfRunoutAreaAngle"] = False

    velocityThalweg = tools.zDelta2velocity(dataThalweg["zdelta"])

    file = tools.getRasterFile(pathDict["pathToOutput"], variable="flux")
    flux = tools.getThalwegValuesFromRaster(file, dataThalweg["x"], dataThalweg["y"])
    pftCrossMax = flux * 10
    # pftCrossMax = np.ones_like(velocityThalweg) * 10

    cfg = cfgUtils.getModuleConfig(ana3AIMEC)
    cfgPlots = cfg["PLOTS"]

    simName = str(pathDict["avalancheDir"]).split("/")[-1]

    outFileNamePart = tools.getOutFileNamePartly(pathDict["titleVariables"])
    pathDict["projectName"] = outFileNamePart
    pathDict["pathResult"] = str(pathDict["savePath"])
    # TODO: we could divide the function outAIMEC.plotVelThAlongThalweg to enable modifications, e.g. the pft representation
    outAIMEC.plotVelThAlongThalweg(pathDict, dataThalweg, pftCrossMax, velocityThalweg, cfgPlots, simName)
