import numpy as np
import pathlib
import logging

import modules.mod3Map.regionalThalwegPlotTools as plotTools
import modules.mod3Map.regionalThalwegAnalysis as regAnalysis
import modules.mod3Map.regionalThalwegAnalysis as regionalThalwegAnalysis
import modules

import avaframe.ana5Utils.preparePathGeneral as pathGen
from avaframe.in3Utils import logUtils


import modules.mod3Map.regionalThalwegTools as tools
from avaframe.in3Utils import cfgHandling
from avaframe.in3Utils import fileHandlerUtils as fU
import avaframe.out3Plot.outAIMEC as outAIMEC
from avaframe.in3Utils import cfgUtils
from avaframe.ana3AIMEC import ana3AIMEC
import avaframe.in1Data.getInput as gI
from avaframe.ana5Utils import DFAPathGeneration
import avaframe.in2Trans.rasterUtils as rasterUtils
from avaframe.out3Plot import outCom3Plots

log = logging.getLogger("avaframe.modules.compareRegionalThalwegPlot")


def regionalThalwegBoxplotCompareMain(avalanchedirList, cfg=None, simhashList=None, studyAreaNames=None):
    """
    run regionalThalweg2DPlotMain for several avalanche directories (study areas)
    and plot their statistic boxplots side by side in one combined figure.

    Parameters
    -----------
    avalanchedirList: list of str or pathlib.Path
        list of avalanche directories, one per study area
    cfg: configparser Object
        contains configuration settings (same cfg used for all study areas)
    simhashList: list of str, optional
        simHash to use per avalanchedir; if None, "" is used for every entry
        (i.e. auto-detected/read from cfg, same as single-area behaviour)
    studyAreaNames: list of str, optional
        label to show on the x-axis of the comparison boxplot for each study area;
        if None, the folder name of the avalanchedir is used

    Returns
    -----------
    pathDictList: list of dict
        the pathDicts collected for each study area (as produced by
        regionalThalweg2DPlotMain), useful if further custom plots are needed
    """
    if cfg is None:
        cfg = cfgUtils.getModuleConfig(regionalThalwegAnalysis)

    cfgDFAPath = cfgUtils.getModuleConfig(
        DFAPathGeneration,
        onlyDefault=cfg["ana5Utils_DFAPathGeneration_override"].getboolean("defaultConfig"),
    )
    # and override with settings from config
    cfgDFAPath, cfg = cfgHandling.applyCfgOverride(cfgDFAPath, cfg, DFAPathGeneration, addModValues=False)

    if simhashList is None:
        simhashList = [""] * len(avalanchedirList)
    if studyAreaNames is None:
        studyAreaNames = [pathlib.Path(d).name for d in avalanchedirList]

    if not (len(avalanchedirList) == len(simhashList) == len(studyAreaNames)):
        message = "avalanchedirList, simhashList and studyAreaNames must have the same length."
        log.error(message)
        raise ValueError(message)

    pathDictList = []
    for avalanchedir, simhash, name in zip(avalanchedirList, simhashList, studyAreaNames):
        pathDict = regAnalysis.regionalThalweg2DPlotMain(
            avalanchedir, cfg, simhash=simhash, studyAreaName=name
        )
        pathDictList.append(pathDict)

    plotTools.plotBoxplot(pathDictList, cfg)



if __name__ == "__main__":

    modPath = pathlib.Path(modules.__file__).resolve().parent
    cfgNameFile = modPath.parent / "atiCfg.ini"
    cfgMain = cfgUtils.getGeneralConfig(nameFile=cfgNameFile)

    avaParentDir = cfgMain["MAIN"]["avalancheDirectory"]

    logName = "runThalwegAnalysis"
    # Start logging
    log = logUtils.initiateLogger(avaParentDir, logName)
    log.info("MAIN SCRIPT")
    log.info("Current avalanche directory: %s", avaParentDir)

    avaParentDir = pathlib.Path(avaParentDir)

    # search for all directory is in avaParentDir
    candidates = sorted([p for p in avaParentDir.iterdir() if p.is_dir()])
    avalancheDirs = [p for p in candidates if (p / "Outputs").is_dir()]
    if len(avalancheDirs) == 0:
        message = f"No valid avalanche directories (containing 'Outputs') found in {avaParentDir}."
        log.error(message)
        raise FileNotFoundError(message)
    log.info(f"Found {len(avalancheDirs)} study areas in {avaParentDir}: {[p.name for p in avalancheDirs]}")

    regionalThalwegBoxplotCompareMain(avalancheDirs)
