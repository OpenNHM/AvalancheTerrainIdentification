# ------------------ Step 08: Make Big Data Structure ------------------- #
#
# Purpose :
#     Build the FlowPy Big Data directory structure by aggregating and arranging
#     all per-PRA, per-size, and per-elevation-band inputs produced in Step 07.
#     The output follows the standardized AvaFrame/FlowPy folder hierarchy:
#
#         SizeN/
#             dry|wet/
#                 Inputs/
#                     REL/
#                     RELArea/
#                     RELID/
#                     RELJSON/
#
# Inputs :
#     - PRA rasters and GeoJSONs prepared in Step 07
#       (./08_praPrepForFlowPy/*.tif / *.geojson)
#
# Outputs :
#     - Fully structured FlowPy Big Data directory:
#         ./09_flowPyBigDataStructure/
#             pra<ID>-<elevRange>-<sizeClass>/SizeN/{dry,wet}/Inputs/{REL,RELArea,RELID,RELJSON}/
#
# Config :
#     [praMAKEBIGDATASTRUCTURE]
#         • usePraBoundary
#         • min/max size class per scenario (dry / wet)
#         • logging settings
#
# Consumes :
#     - Step 07 outputs (PRA → FlowPy preparation)
#
# Provides :
#     - FlowPy-ready directory tree for Step 09 (parameterization) and Step 10 (FlowPy run)
#
# Author :
#     Christoph Hesselbach
#
# Institution :
#     Austrian Research Centre for Forests (BFW)
#     Department of Natural Hazards | Snow and Avalanche Unit
#
# Date & Version :
#   2025-11 - 1.0
#
# ----------------------------------------------------------------------- #


import os
import re
import glob
import time
import shutil
import logging
from typing import Optional

import modules.mod0Helper.dataUtils as dataUtils

log = logging.getLogger("avaframe.ati.praMakeBigDataStructure")


def _discoverInputFolder(workFlowDir) -> str:
    """Return the flat Step-07 output directory containing per-(band,size) files."""
    cairosDir = workFlowDir["cairosDir"]
    return workFlowDir.get("praPrepForFlowPyDir") or os.path.join(
        cairosDir, "08_praPrepForFlowPy"
    )


def _ensureOutputRoot(workFlowDir):
    """Ensure and return the flat Step-08 output root."""
    cairosDir = workFlowDir["cairosDir"]
    bigDataRoot = workFlowDir.get("praMakeBigDataStructureDir") or os.path.join(
        cairosDir, "09_flowPyBigDataStructure"
    )
    os.makedirs(bigDataRoot, exist_ok=True)
    return bigDataRoot


def _iterTifs(inputFolder):
    """List direct Step-07 TIFF outputs, ignoring obsolete nested layouts."""
    return sorted(glob.glob(os.path.join(inputFolder, "*.tif")))


def _extractSizeNumberFromBase(baseName: str) -> Optional[int]:
    """Extract size class number (4th token in praXXX-YYYY-ZZZZ-N filenames)."""
    parts = baseName.split("-")
    if len(parts) >= 4:
        try:
            return int(parts[3])
        except ValueError:
            return None
    return None


def _logDirectoryTree(baseDir, cairosDir, level=logging.INFO):
    """Optional full directory tree logger."""
    baseDir = os.path.abspath(baseDir)
    log.log(level, "Directory tree for ./%s", dataUtils.relPath(baseDir, cairosDir))
    for root, dirs, files in os.walk(baseDir):
        depth = os.path.relpath(root, start=baseDir).count(os.sep)
        indent = "    " * depth
        log.log(level, "%s%s/", indent, os.path.basename(root))
        subIndent = "    " * (depth + 1)
        for f in sorted(files):
            log.log(level, "%s%s", subIndent, f)


# ------------------ Main driver ------------------ #


def runPraMakeBigDataStructure(cfg, workFlowDir):
    """
    Step 08: Build FlowPy input folder structure and copy PRA rasters and GeoJSONs.
    Supports separate min/max size caps for dry and wet avalanches.
    """
    tAll = time.perf_counter()

    # --- Config ---
    streamThreshold = cfg["praSUBCATCHMENTS"].getint("streamThreshold", fallback=500)
    minLength = cfg["praSUBCATCHMENTS"].getint("minLength", fallback=100)
    smoothingWindowSize = cfg["praSUBCATCHMENTS"].getint("smoothingWindowSize", fallback=5)
    sizeFilter = cfg["praSEGMENTATION"].getfloat("sizeFilter", fallback=500.0)

    sect = cfg["praMAKEBIGDATASTRUCTURE"]
    usePraBoundary = sect.getboolean("usePraBoundary", fallback=False)
    minDrySizeClass = sect.getint("minDrySizeClass", fallback=2)
    maxDrySizeClass = sect.getint("maxDrySizeClass", fallback=5)
    minWetSizeClass = sect.getint("minWetSizeClass", fallback=2)
    maxWetSizeClass = sect.getint("maxWetSizeClass", fallback=4)
    logDirectoryTree = sect.getboolean("logDirectoryTree", fallback=False)

    # --- Directories ---
    cairosDir = workFlowDir["cairosDir"]
    inputFolder = _discoverInputFolder(workFlowDir)
    outCaseDir = _ensureOutputRoot(workFlowDir)

    log.info(
        "...MakeBigData using: in=./%s, out=./%s, streamThr=%s, minLen=%s, smoothWin=%s, sizeF=%s, usePraBoundary=%s",
        dataUtils.relPath(inputFolder, cairosDir),
        dataUtils.relPath(outCaseDir, cairosDir),
        streamThreshold,
        minLength,
        smoothingWindowSize,
        int(sizeFilter),
        usePraBoundary,
    )

    # --- Collect rasters ---
    allTifs = _iterTifs(inputFolder)
    if not allTifs:
        log.error("No .tif rasters found in ./%s", dataUtils.relPath(inputFolder, cairosDir))
        return

    praAttribute = cfg["praPREPFORFLOWPY"].get("rasterizeAttributePRA", fallback="praAreaM")
    praIdAttribute = cfg["praPREPFORFLOWPY"].get("rasterizeAttributeID", fallback="praID")
    releaseSuffix = "-praBound.tif" if usePraBoundary else f"-{praAttribute}.tif"
    releaseStemSuffix = os.path.splitext(releaseSuffix)[0]
    releaseTifs = [
        path
        for path in allTifs
        if os.path.basename(path).startswith("pra") and path.endswith(releaseSuffix)
    ]
    if not releaseTifs:
        log.error(
            "No release rasters ending in '%s' found in ./%s",
            releaseSuffix,
            dataUtils.relPath(inputFolder, cairosDir),
        )
        return

    for t in releaseTifs:
        log.debug("Using raster: ./%s", dataUtils.relPath(t, cairosDir))

    # --- Build structure and copy rasters ---
    nFoldersCreated = nCopied = nSkipped = 0

    def _copyInput(srcPath, dstDir, label):
        nonlocal nCopied
        if not os.path.exists(srcPath):
            log.warning("Missing %s for case: ./%s", label, dataUtils.relPath(srcPath, cairosDir))
            return
        dstPath = os.path.join(dstDir, os.path.basename(srcPath))
        try:
            shutil.copy2(srcPath, dstPath)
            nCopied += 1
            log.debug(
                "Copied %s: ./%s -> ./%s",
                label,
                dataUtils.relPath(srcPath, cairosDir),
                dataUtils.relPath(dstPath, cairosDir),
            )
        except Exception:
            log.exception("Copy failed for %s to ./%s", label, dataUtils.relPath(dstDir, cairosDir))

    for tifPath in releaseTifs:
        try:
            with dataUtils.timeIt(f"makeCase({os.path.basename(tifPath)})"):
                fileStem = os.path.splitext(os.path.basename(tifPath))[0]

                # --- Remove the configured release-raster suffix from the scenario name. ---
                folderBase = fileStem.removesuffix(releaseStemSuffix)
                folderBase = folderBase.removesuffix("-ElevBands-Sized")
                log.debug("Scenario folder base parsed: %s -> %s", fileStem, folderBase)

                # --- extract size number ---
                sizeNum = _extractSizeNumberFromBase(folderBase)
                if sizeNum is None:
                    nSkipped += 1
                    log.warning("Could not extract size number from '%s'; skipping.", fileStem)
                    continue

                # --- ensure case root ---
                caseRoot = os.path.join(outCaseDir, folderBase)
                os.makedirs(caseRoot, exist_ok=True)

                # --- per-flowType + size subtrees ---
                for flowType in ("dry", "wet"):
                    if flowType == "dry":
                        minSize = minDrySizeClass
                        maxSize = min(maxDrySizeClass, sizeNum)
                    else:
                        minSize = minWetSizeClass
                        maxSize = min(maxWetSizeClass, sizeNum)

                    for size in range(minSize, maxSize + 1):
                        relDir = os.path.join(caseRoot, f"Size{size}", flowType, "Inputs", "REL")
                        relAreaDir = os.path.join(caseRoot, f"Size{size}", flowType, "Inputs", "RELArea")
                        relIdDir = os.path.join(caseRoot, f"Size{size}", flowType, "Inputs", "RELID")
                        relJsonDir = os.path.join(caseRoot, f"Size{size}", flowType, "Inputs", "RELJSON")
                        os.makedirs(relDir, exist_ok=True)
                        os.makedirs(relIdDir, exist_ok=True)
                        os.makedirs(relJsonDir, exist_ok=True)
                        os.makedirs(relAreaDir, exist_ok=True)
                        nFoldersCreated += 1

                        # --- Copy release raster and its required companion rasters ---
                        _copyInput(tifPath, relDir, "release raster")
                        _copyInput(
                            os.path.join(inputFolder, f"{folderBase}-{praAttribute}.tif"),
                            relAreaDir,
                            "release-area raster",
                        )
                        _copyInput(
                            os.path.join(inputFolder, f"{folderBase}-{praIdAttribute}.tif"),
                            relIdDir,
                            "release-ID raster",
                        )

                        # --- Copy matching GeoJSON (if exists) ---
                        geoBase = folderBase + ".geojson"
                        geojsonSearch = os.path.join(inputFolder, geoBase)
                        if os.path.exists(geojsonSearch):
                            dstJson = os.path.join(relJsonDir, os.path.basename(geojsonSearch))
                            try:
                                shutil.copy2(geojsonSearch, dstJson)
                                log.debug(
                                    "Copied GeoJSON: ./%s -> ./%s",
                                    dataUtils.relPath(geojsonSearch, cairosDir),
                                    dataUtils.relPath(dstJson, cairosDir),
                                )
                            except Exception:
                                log.exception(
                                    "Copy failed for GeoJSON to ./%s",
                                    dataUtils.relPath(relJsonDir, cairosDir),
                                )
                        else:
                            log.debug("No GeoJSON found for base=%s", folderBase)

        except Exception:
            log.exception("Case creation failed for ./%s", dataUtils.relPath(tifPath, cairosDir))

    # --- optional directory tree log ---
    if logDirectoryTree:
        _logDirectoryTree(outCaseDir, cairosDir)

    log.info(
        "...MakeBigData stats: cases=%d, rasters_copied=%d, skipped=%d", nFoldersCreated, nCopied, nSkipped
    )
    log.info("...MakeBigData - done: %.2fs", time.perf_counter() - tAll)
