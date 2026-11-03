"""
Plotting functions for regional thalweg plots
"""

import numpy as np
import logging
from cmcrameri import cm as cmapCrameri
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm
import matplotlib.patheffects as pe
from matplotlib.patches import Patch
import geopandas as gpd

import modules.mod3Map.regionalThalwegTools as tools
import modules.mod0Helper.helpFunctions as helper
import avaframe.in2Trans.rasterUtils as rasterUtils
import avaframe.in1Data.getInput as gI
import avaframe.out3Plot.plotUtils as pU

# create local logger
log = logging.getLogger("avaframe.modules.regionalThalwegPlotTools")


def plotField(ax, fig, pathDict, variable):
    """plots hillshade of the DEM and the output raster of the simulation zoomed in to the simulation extent

    Parameters:
    -----------
    ax: matplotlib axis
        axis in which the hillshade and output raster is plotted
    fig: matplotlib figure
        figure to that the plot belongs to
    pathDict: dict
        contains simulation paths
    variable: str
        output variable that is plotted (of whole simulation)

    Returns:
    -----------
    ax: matplotlib axis
        axis containing hillshade and output raster of simulation
    """
    demDict = gI.readDEM(pathDict["avalancheDir"])
    dem = demDict["rasterData"]
    header = demDict["header"]
    cellSize = header["cellsize"]
    clabel = {
        "zdelta": "max. zDelta [m]",
        "fpTravelAngle": "Max. travel angle [°]",
        "travelLength": "Max. travel length [m]",
        "velocityMax": "Max. velocity [m/s]",
        "flux": "Max. flux",
        "": "",
    }
    # name of the result raster (file name ending) of the plotted variable
    rasterNames = {
        "zdelta": "zdelta",
        "fpTravelAngle": "fpTravelAngleMax",
        "travelLength": "travelLengthMax",
        "velocityMax": "zdelta",
        "flux": "flux",
    }
    # also accept the raster names directly
    variable = {"fpTravelAngleMax": "fpTravelAngle", "travelLengthMax": "travelLength"}.get(
        variable, variable
    )
    if variable not in clabel:
        message = f"plotVariable = {variable} is not valid, choose one of {list(clabel)}."
        log.error(message)
        raise ValueError(message)
    variableOut = rasterNames.get(variable, "")
    if variable == "":
        raster = np.zeros_like(dem)
        raster[:] = np.nan
    else:
        file = tools.getRasterFile(pathDict["pathToOutput"], variable=variableOut)
        rasterDict = rasterUtils.readRaster(file)
        raster = rasterDict["rasterData"]
    if variable == "velocityMax":
        raster = helper.zDelta2velocity(raster)

    # rasterPraDict = rasterUtils.readRaster(praPath)
    # rasterPra = rasterPraDict["rasterData"]

    rowsMin, rowsMax, colsMin, colsMax = pU.constrainPlotsToData(raster, header["cellsize"], buffer=150)
    rowsMin = int(rowsMin)
    rowsMax = int(rowsMax)
    colsMin = int(colsMin)
    colsMax = int(colsMax)
    dataConstrained = raster[rowsMin : rowsMax + 1, colsMin : colsMax + 1]
    demConstrained = dem[rowsMin : rowsMax + 1, colsMin : colsMax + 1]
    # praConstrained = rasterPra[rowsMin : rowsMax + 1, colsMin : colsMax + 1]

    data = np.ma.masked_where(dataConstrained == 0.0, dataConstrained)
    dataConstrained = np.ma.masked_where(dataConstrained == 0.0, dataConstrained)

    # set 0 and smaller to np.nan
    # praConstrained = np.where(praConstrained > 0, 1.0, np.nan)

    # Set extent of peak file
    ny = data.shape[0]
    nx = data.shape[1]
    Ly = ny * cellSize
    Lx = nx * cellSize

    extentCellCenters, extentCellCorners, rowsMinPlot, rowsMaxPlot, colsMinPlot, colsMaxPlot = (
        pU.createExtent(rowsMin, rowsMax, colsMin, colsMax, header)
    )

    _, _ = pU.addHillShadeContours(ax, demConstrained, cellSize, extentCellCenters)

    extent = extentCellCenters
    extentPlot = [
        extent[0] - 0.5 * cellSize,
        extent[1] + 0.5 * cellSize,
        extent[2] - 0.5 * cellSize,
        extent[3] + 0.5 * cellSize,
    ]

    CS = ax.contour(
        demConstrained, levels=np.arange(0, 3500, 100), extent=extentPlot, colors="dimgrey", linewidths=0.5
    )
    ax.clabel(CS, CS.levels[::2], inline=True, fontsize=9)
    # dataOneColor = np.where(dataConstrained > 0.0, np.amax(data)*0.25, np.nan)
    colorsS = ["#FFCEF4", "#FFA7A8", "#C19A1B", "#578B21", "#007054", "#004960", "#201158"]
    cmapS = cmapCrameri.batlow.reversed()
    levels = 7
    bounds = np.round(
        np.linspace(np.nanmin(dataConstrained), np.nanmax(dataConstrained), levels + 1)
    )  # Define boundaries
    norm = BoundaryNorm(bounds, ncolors=cmapS.N, clip=True)  # Create a norm based on the boundaries

    if variable != "":
        f = ax.imshow(
            dataConstrained,
            cmap=cmapS,
            norm=norm,
            extent=extentCellCorners,
            origin="lower",
            aspect="equal",
            zorder=4,
            alpha=0.5,
        )
        fig.colorbar(f, ax=ax, label=clabel[variable], shrink=0.8, aspect=30, pad=0.02)

    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")

    ax.set_xticks(ax.get_xticks()[::3])
    ax.set_yticks(ax.get_yticks()[::3])

    # Shift tick labels closer to the axes (reduce padding)
    ax.tick_params(axis="x", pad=1.5)
    ax.tick_params(axis="y", pad=1.5)

    return ax


def makeFieldPlot(ax, fig, cfg, pathDict, xThalweg, yThalweg, dataThalweg):
    """make a raster plot for FlowPy output

    Parameters
    -----------
    ax: matplotlib axis
        Axis for the plot
    fig: matplotlib figure
        Figure for the plot
    cfg: configparser
        settings
    pathDict: dict
        contains simulation paths
    xThalweg: numpy array
        x coordinates of all thalwegs
    yThalweg: numpy array
        y coordinates of all thalwegs
    dataThalweg: dict or None
        profile of thalweg that is highlighted here (None: no thalweg is highlighted)

    Returns
    -----------
    fig: matplotlib figure
        Figure containing the plot
    ax: matplotlib axis
        Axis containing the plot
    """
    colorThalweg = "m"
    variable = cfg["GENERAL"].get("plotVariable")
    thalwegPra = cfg["GENERAL"].getboolean("thalwegPra")
    centerOf = pathDict["titleVariables"]["centerOf"]
    colorPra = cfg["GENERAL"].get("colorPra")

    ax = plotField(ax, fig, pathDict, variable)
    # ax.scatter(xThalweg, yThalweg, c="r", s=0.3, zorder=5, label=f"thalweg {centerOf}")
    # ax.scatter(xThalweg[0], yThalweg[0], c="b", s=2.0, zorder=6, label="startcell")
    for i, (x, y) in enumerate(zip(xThalweg, yThalweg)):
        # all thalwegs are only plotted when in cfg: relId is empty
        ax.plot(x, y, "-", c="k", linewidth=1, zorder=5, label=f"Thalweg" if i == 0 else None)
    if dataThalweg is not None:
        ax.plot(dataThalweg["x"], dataThalweg["y"], "-", c=colorThalweg, zorder=6)
    ax.legend()

    if thalwegPra:
        ax = addReleaseAreaToPlot(ax, pathDict, colorPra=f"#{colorPra}", linewidth=0.7)
    return fig, ax


def makeThalwegPlot(ax, dataThalweg, pathDict, colorPra=""):
    """make a 2D thalweg plot for FlowPy output

    Parameters
    -----------
    ax: matplotlib axis
        Axis for the plot
    dataThalweg: dict
        contains thalweg data:
        s or travelLength (np.array): travel length along thalweg
        z or altitude (np.array): altitude along thalweg
        zDelta (np.array): velocity altitude along thalweg
        alpha (float or int): input parameter of the simulation: alpha angle
        exp (float or int): input parameter of the simulation: exponent
        zDeltaMaxInput (float or int): input parameter of the simulation: zDelta Maximum threshold
    pathDict: dict
        contains paths
    centerOf: str
        which center of is used (possible: '' (default),'CoE', 'CoZd', 'CoF')

    Returns
    -----------
    ax: matplotlib axis
        Axis containing the thalweg plot
    """
    z = np.array(dataThalweg["z"])
    s = np.array(dataThalweg["s"])
    zdelta = np.array(dataThalweg["zdelta"], dtype=float)
    sExtended = np.array(dataThalweg["s"])
    zExtended = np.array(dataThalweg["z"])
    indStart = dataThalweg["indStartMassAverage"]
    indEnd = dataThalweg["indEndMassAverage"]

    # process path: polygon of the release area (if available), otherwise cells with flux > 0
    titleRelId = pathDict["titleVariables"]["relId"]
    relId = int(titleRelId) if str(titleRelId) != "" else None
    pathPolygons = tools.getPathPolygons(pathDict["pathToOutput"]) if relId is not None else None
    _, indInPath = tools.getProfileInPath(pathDict["pathToOutput"], dataThalweg, relId, pathPolygons)
    if indInPath.size == 0:
        log.warning(
            "No point of the thalweg is within the process path, the thalweg profile is not plotted."
        )
        ax.text(
            0.5, 0.5, "thalweg not within the process path", ha="center", va="center", transform=ax.transAxes
        )
        return ax

    maskNan = np.ones(zdelta.shape, dtype=bool)
    maskNan[indInPath] = False
    zdelta[maskNan] = np.nan
    s[maskNan] = np.nan
    z[maskNan] = np.nan

    # FlowPy input parameter
    alpha = dataThalweg.get("alpha", None)

    # location of the max. zDelta along the extended thalweg
    s_max = s[zdelta == np.nanmax(zdelta)]
    z_max = z[zdelta == np.nanmax(zdelta)]
    zdelta_max = zdelta[zdelta == np.nanmax(zdelta)]
    # effective max. zDelta along the averaged thalweg (same value as in the statistic plots)
    zdeltaEffMax = dataThalweg.get("zdeltaEffMax", zdelta_max[0])

    # effective runout angle (as alphaEff in the statistic plots): from the first to the last point of
    # the extended thalweg within the process path (same section as travelLengthMax)
    indA = indInPath[0]
    indB = indInPath[-1]
    angle_degrees = tools.computeRunoutAngle(zExtended[indA : indB + 1], sExtended[indA : indB + 1])
    ds = sExtended[indB] - sExtended[indA]
    dz = zExtended[indA] - zExtended[indB]

    if alpha is not None:
        dh = ds * np.tan(np.deg2rad(alpha))
        ax.hlines(
            zExtended[indA] - dh,
            sExtended[indA] + ds * 0.85,
            sExtended[indA] + ds,
            colors="k",
            linestyles="dotted",
            linewidths=0.7,
        )

    # dummy for legend group
    (dummyGeom,) = ax.plot(np.nan, np.nan, linestyle="none", label="Thalweg geometry")
    # ax.plot(sExtended, zExtended, c="gray", linestyle="-", label="z")
    (thalwegTop,) = ax.plot(
        sExtended[: indStart + 1],
        zExtended[: indStart + 1],
        "-y.",
        label="z: top extension",
        lw=2,
        path_effects=[pe.Stroke(linewidth=3, foreground="b"), pe.Normal()],
    )
    (thalwegBot,) = ax.plot(
        sExtended[indEnd:],
        zExtended[indEnd:],
        "-y.",
        label="z: bottom extension",
        lw=2,
        path_effects=[pe.Stroke(linewidth=3, foreground="g"), pe.Normal()],
    )
    (thalweg,) = ax.plot(
        sExtended[indStart : indEnd + 1],
        zExtended[indStart : indEnd + 1],
        "-y.",
        label="z",
        lw=2,
        path_effects=[pe.Stroke(linewidth=3, foreground="k"), pe.Normal()],
    )
    l = ax.legend(handles=[dummyGeom, thalweg, thalwegTop, thalwegBot], loc="upper center")
    ax.add_artist(l)
    # dummy for legend group
    inputHandles = []
    if alpha is not None:
        (p1,) = ax.plot(np.nan, np.nan, linestyle="none", label="Model input\nparameter")
        (p2,) = ax.plot(
            [sExtended[indA], sExtended[indA] + ds],
            [zExtended[indA], zExtended[indA] - dh],
            "k--",
            linewidth=0.7,
            label=rf"""$\alpha_{{input}}$ = {np.round(alpha, 1)}°""",
        )
        inputHandles = [p1, p2]
    # dummy for legend group
    (p3,) = ax.plot(np.nan, np.nan, linestyle="none", label="Model results &\nderived metrics")
    zDeltaType = dataThalweg.get("zdeltaType", None)
    zDeltaTypeLabel = f" ({tools.getZDeltaLabel(zDeltaType)})" if zDeltaType is not None else ""
    (p4,) = ax.plot(s, [d + z for d, z in zip(z, zdelta)], "r", lw=2, label=f"$z^{{vel}}${zDeltaTypeLabel}")
    if colorPra != "":
        ax.scatter(
            s[indInPath[0]],
            z[indInPath[0]],
            s=30,
            zorder=10,
            color=f"#{colorPra}",
        )

    p5 = ax.vlines(
        s_max[0],
        z_max[0],
        z_max[0] + zdelta_max[0],
        label="$v_{max}$ = " + str(np.round(tools.zDelta2velocity(zdeltaEffMax), 1)) + " m/s",
    )
    (p6,) = ax.plot(
        [sExtended[indA], sExtended[indB]],
        [zExtended[indA], zExtended[indB]],
        color="k",
        linestyle="--",
        linewidth=1.1,
        label=rf"""$\alpha_{{eff}}$ = {np.round(angle_degrees, 1)}°""",
        zorder=20,
    )

    (p7,) = ax.plot(
        [sExtended[indA], sExtended[indB]],
        [zExtended[indB]] * 2,
        color="grey",
        linewidth=1,
        linestyle="--",
        label=rf"""$\Delta$s = {np.round(ds, 1)} m""",
    )
    p8 = ax.vlines(
        x=sExtended[indA],
        ymin=zExtended[indB],
        ymax=zExtended[indA],
        color="silver",
        linestyle="--",
        linewidth=1,
        label=(rf"$\Delta z = {np.round(dz, 1)}$ m"),
    )

    ax.set(xlabel="Horizontal distance [m]")
    ax.set(ylabel="Elevation [m]")
    ax.legend(handles=inputHandles + [p3, p4, p5, p6, p7, p8], loc="upper right")  # , bbox_to_anchor=(1, 1))

    return ax


def plotBoxplot(pathDictList, cfg, title=""):
    """
    shows and potentially saves Violinplot and Boxplot for one or several study areas

    Parameters:
    -----------
    pathDictList: dict or list of dict
        one pathDict (single study area) or a list of pathDicts
        (one boxplot per study area, plotted side by side). Each pathDict should
        contain "pathToOutput", "savePath", "titleVariables" (with "simHash"),
        and optionally "studyAreaName" for the x-axis label.
    cfg: configparser Object
        contains configuration settings
    title: str
        title for the plot
    """
    # allow calling with a single pathDict like before
    if isinstance(pathDictList, dict):
        pathDictList = [pathDictList]

    cfgGen = cfg["GENERAL"]
    cfgSize = cfg["SIZECLASS"]
    varName = cfgGen.get("statisticVariable")
    centerOf = cfgGen.get("centerOfVariable")
    zDeltaType = cfgGen.get("zDeltaThalweg")
    ylabel = tools.getYlabelBoxplot(varName, zDeltaType)

    # --- collect data + labels for every study area ---
    dataList = []
    labels = []
    for pathDict in pathDictList:
        path = pathDict["pathToOutput"]
        dataNan = tools.getDataBoxplots(path, varName, centerOf, cfgGen.getfloat("rho"), zDeltaType)
        data = np.delete(dataNan, np.where(np.isnan(dataNan)))
        dataList.append(data)
        areaName = pathDict.get("studyAreaName", pathDict["titleVariables"]["simHash"])
        log.info(f"{areaName}: median {varName} = {np.nanmedian(data)}")
        labels.append(f"{areaName}\n(n = {len(data)})")

    nGroups = len(dataList)
    positions = np.arange(1, nGroups + 1)

    fig, ax2 = plt.subplots(figsize=(max(4, 1.4 * nGroups + 1.5), 5))
    fig.subplots_adjust(left=0.15, right=0.95, top=0.92, bottom=0.18)
    if cfgGen.getboolean("plotLogScale"):
        ax2.set_yscale("log")

    ax2.violinplot(dataList, positions=positions)
    ax2.boxplot(
        dataList,
        positions=positions,
        whis=0,
        widths=0.07,
        showfliers=False,
        medianprops={"color": "blue"},
        zorder=5,
    )
    ax2.set_xticks(positions, labels=labels, fontsize=13)
    ax2.set_xlim(0.25, nGroups + 0.75)

    # y limits: from the configuration (if set), otherwise defaults for some variables
    yLimDefaults = {"alphaIn": (19, 36), "velocity": (-1, 50)}
    yMin, yMax = yLimDefaults.get(varName, (None, None))
    if cfgGen["boxplotYlimMin"] != "":
        yMin = cfgGen.getfloat("boxplotYlimMin")
    if cfgGen["boxplotYlimMax"] != "":
        yMax = cfgGen.getfloat("boxplotYlimMax")
    ax2.set_ylim(bottom=yMin, top=yMax)

    # --- color background (size classes) - only depends on varName/ylim ---
    varLabel = None
    if "travelLength" in varName:
        varLabel = "travelLength"
        sizeName = "Runout\nsize"
    elif "impressure" in varName:
        varLabel = "impressure"
        sizeName = "Destructive\nsize"
    elif "relArea" in varName:
        varLabel = "relArea"
        sizeName = "Dimension\nsize"

    tools.logOverallStatistic(dataList, cfgSize, varLabel)

    if varLabel is not None:
        ysize1Max = cfgSize.getint(f"{varLabel}Size1Max")
        ysize2Max = cfgSize.getint(f"{varLabel}Size2Max")
        ysize3Max = cfgSize.getint(f"{varLabel}Size3Max")
        ysize4Max = cfgSize.getint(f"{varLabel}Size4Max")

        ysize1MaxCom = cfgSize.getint(f"{varLabel}Size1MaxCom")
        ysize2MaxCom = cfgSize.getint(f"{varLabel}Size2MaxCom")
        ysize3MaxCom = cfgSize.getint(f"{varLabel}Size3MaxCom")
        ysize4MaxCom = cfgSize.getint(f"{varLabel}Size4MaxCom")

        y_min, y_m = ax2.get_ylim()
        y_max = np.max([y_m, 1.1 * ysize4Max])
        ax2.axhspan(0, ysize1Max, facecolor="#" + cfgSize["colorSize1"], alpha=0.15, zorder=1)
        ax2.axhspan(ysize1Max, ysize2Max, facecolor="#" + cfgSize["colorSize2"], alpha=0.15, zorder=1)
        ax2.axhspan(ysize2Max, ysize3Max, facecolor="#" + cfgSize["colorSize3"], alpha=0.15, zorder=1)
        ax2.axhspan(ysize3Max, ysize4Max, facecolor="#" + cfgSize["colorSize4"], alpha=0.15, zorder=1)
        ax2.axhspan(ysize4Max, y_max, facecolor="#" + cfgSize["colorSize5"], alpha=0.15, zorder=1)

        class_lab = ""
        y_min, y_m = ax2.get_ylim()
        y_max = np.max([y_m, 1.1 * ysize4Max])
        textX = 0.4
        ax2.text(
            textX,
            0 + (ysize1Max * 0.75),
            f"{class_lab} 1",
            ha="center",
            va="center",
            color="#" + cfgSize["colorSize1"],
            fontsize=13,
        )
        ax2.text(
            textX,
            ysize1Max + (ysize2Max - ysize1Max) / 2,
            f"{class_lab} 2",
            ha="center",
            va="center",
            color="#008000",
            fontsize=13,
        )
        ax2.text(
            textX,
            ysize2Max + (ysize3Max - ysize2Max) / 2,
            f"{class_lab} 3",
            ha="center",
            va="center",
            color="#ff9a00",
            fontsize=13,
        )
        ax2.text(
            textX,
            ysize3Max + (ysize4Max - ysize3Max) / 2,
            f"{class_lab} 4",
            ha="center",
            va="center",
            color="#" + cfgSize["colorSize4"],
            fontsize=13,
        )
        ax2.text(
            textX,
            ysize4Max + (y_max - ysize4Max) / 5,
            f"{class_lab} 5",
            ha="center",
            va="center",
            color="#" + cfgSize["colorSize5"],
            fontsize=13,
            zorder=5,
        )

        ax2.text(
            textX + 0.23,
            0.98,
            sizeName,
            transform=ax2.get_xaxis_transform(),
            ha="center",
            va="top",
            color="gray",
            bbox=dict(facecolor="#ededed", alpha=0.7, edgecolor="none"),
            fontsize=12,
            zorder=3,
        )
        ax2.set_yticks([ysize1Max, ysize2Max, ysize3Max, ysize4Max])
        ax2.set_yticklabels([ysize1MaxCom, ysize2MaxCom, ysize3MaxCom, ysize4MaxCom], fontsize=13)
        ax2.minorticks_off()

    plt.ylabel(ylabel, fontsize=13)
    if title == "" and len(pathDictList) == 1:
        title = f"thalwege {centerOf}"
    plt.title(title)
    plt.grid(True)

    # --- save: combine info from all study areas ---
    savePath = pathDictList[0]["savePath"]
    simhashCombined = "-".join(pd["titleVariables"]["simHash"] for pd in pathDictList)
    zdSuffix = (
        f"_{tools.getZDeltaFileSuffix(zDeltaType)}" if tools.isSimulatedZDeltaVariable(varName) else ""
    )
    filename = f"ThalwegStatistic_{simhashCombined}_{varName}_{centerOf}{zdSuffix}.png"
    fig.savefig(savePath / filename)
    plt.close(fig)
    log.info(f"Saved boxplot as {savePath / filename}")


def addPolygonToPlot(fileToPolygon, ax, color="#6900D1", linewidth=1.0, label=""):
    """
    add a polygon to a plot and its legend

    Parameters
    --------------
    fileToPolygon: pathlib Path
        path to file
    ax: plt.axis
        axis in which polygon is plotted
    color: str
        color of polygon
    linewidth: float
        linewidth of polygons
    label: str
        label for legend

    Returns
    ----------
    ax: plt.axis
        axis with added polygon
    """

    poygon = gpd.read_file(fileToPolygon)
    poygon.plot(ax=ax, edgecolor=color, linewidth=linewidth, facecolor="none", zorder=10)
    relPatch = Patch(edgecolor=color, facecolor="white", label=label)
    handles, labels = ax.get_legend_handles_labels()
    handles.append(relPatch)
    ax.legend(handles=handles)

    return ax


def addReleaseAreaToPlot(ax, pathDict, colorPra, linewidth=1):
    """
    if a release area in shp or geojson format is provided, add it to the plot

    Parameters
    -------------------
    ax: plt.axis
        axis in which release area is plotted
    pathDict: dict
        contains paths to avalacnhe directory
    colorPra: str
        color of PRAs
    linewidth: float
        line width of PRAs

    Returns
    ----------
    ax: plt.axis
        axis with added release area
    """

    relDir = pathDict["avalancheDir"] / "Inputs" / "RELJSON"
    filePath = tools.getRasterFile(relDir, variable="", ext="shp")
    if filePath == "":
        filePath = tools.getRasterFile(relDir, variable="", ext="geojson")
    if filePath != "":
        ax = addPolygonToPlot(filePath, ax, color=colorPra, linewidth=linewidth, label="Release area")
    else:
        log.info("No polygon file for a release area is found.")
    return ax


def plotEffectiveVsInputScatter(pathDictList, cfg, title=""):
    """
    scatter plot with a linear regression line for
    - effective runout angle vs. input alpha angle
    - effective runout angle starting at the release area top vs. input alpha angle
    - effective runout angle of the averaged (not extended) thalweg vs. input alpha angle
    - averaged travel angle (gamma) at the runout end vs. input alpha angle
    - effective runout angle of the averaged thalweg vs. averaged travel angle (gamma) at the runout end
    - effective max. velocity vs. input max. velocity
    One plot is created per study area (scatter + regression line); the travel angle
    and the velocity pair are shown as two panels of one figure (ThalwegRegression_TravelAngleVelocity_*). Plus one
    combined plot per variable pair showing only the regression lines of all
    study areas together for comparison (no scatter points there).
    A y = x reference line is added to every plot, and x- and y-axis share
    the same limits so the y = x line is shown as a true diagonal.

    For the velocity pair, size-class background shading is added, using the
    same colors as plotBoxplot: horizontal bands for the effective max.
    velocity (converted from the impressure size-class pressure limits), and
    vertical bands for the input max. velocity (SIZECLASS velocityInSize1Max .. velocityInSize4Max).
    Both are clipped to the region below the y = x diagonal,
    since they are shown starting from the left/bottom axis up to the
    diagonal. Since the input velocity boundaries no longer depend on the
    DEM, both shadings are identical for every study area and are therefore
    also shown in the combined plot.

    Parameters
    ------------
    pathDictList: list of dict
        one pathDict per study area (as produced by regionalThalwegAnalysisMain),
        must contain "pathToOutput", "savePath", "titleVariables" and
        optionally "studyAreaName"
    cfg: configparser Object
        contains configuration settings
    title: str
        title prefix for the plots
    """
    if isinstance(pathDictList, dict):
        pathDictList = [pathDictList]

    cfgGen = cfg["GENERAL"]
    cfgSize = cfg["SIZECLASS"]
    centerOf = cfgGen.get("centerOfVariable")
    rho = cfgGen.getfloat("rho")
    zDeltaType = cfgGen.get("zDeltaThalweg")
    zdSuffix = f"_{tools.getZDeltaFileSuffix(zDeltaType)}"

    # TODO: choose which alpha effective are useful!!!

    varPairs = [
        ("alphaIn", "alphaEff", "Input alpha angle [°]", "Effective runout angle [°]", "RunoutAngle"),
        (
            "alphaIn",
            "alphaEffRelTop",
            "Input alpha angle [°]",
            "Effective runout angle from release area top [°]",
            "RunoutAngleReleaseTop",
        ),
        (
            "alphaIn",
            "alphaEffAveraged",
            "Input alpha angle [°]",
            "Effective runout angle of averaged thalweg [°]",
            "RunoutAngleAveraged",
        ),
        (
            "alphaIn",
            "gammaEnd",
            "Input alpha angle [°]",
            "Averaged travel angle at runout end [°]",
            "TravelAngle",
        ),
        (
            "gammaEnd",
            "alphaEffAveraged",
            "Averaged travel angle at runout end [°]",
            "Effective runout angle of averaged thalweg [°]",
            "RunoutAngleAveragedVsTravelAngle",
        ),
        (
            "velocityIn",
            "velocityEff",
            "Input max. velocity [m/s]",
            f"Effective max. velocity [m/s]\n(zDelta {tools.getZDeltaLabel(zDeltaType)})",
            "Velocity",
        ),
    ]

    # collect data once per study area (reused for individual + combined plots)
    allData = []
    allNames = []
    for pathDict in pathDictList:
        data = tools.getEffectiveValues(pathDict["pathToOutput"], centerOf, zDeltaType=zDeltaType, rho=rho)
        allData.append(data)
        allNames.append(pathDict.get("studyAreaName", pathDict["titleVariables"]["simHash"]))

    savePath = pathDictList[0]["savePath"]
    simhashCombined = "-".join(pd["titleVariables"]["simHash"] for pd in pathDictList)

    sizeColors = [f"#{cfgSize[f'colorSize{i}']}" for i in range(1, 6)]

    # --- horizontal (effective velocity) class boundaries from impressure size classes ---
    yVelBoundaries = [
        tools.pressure2velocity(cfgSize.getint(f"impressureSize{i}Max"), rho) for i in range(1, 5)
    ]

    # --- vertical (input velocity) class boundaries ---
    # input velocity class boundaries (SIZECLASS velocityInSize1Max .. velocityInSize4Max)
    xVelBoundaries = [
        cfgSize.getfloat(f"velocityInSize{i}Max", fallback=default)
        for i, default in zip(range(1, 5), [15, 30, 45, 60])
    ]

    # per study area, these pairs are plotted side by side in one figure instead of separate figures
    panelTags = ["TravelAngle", "Velocity"]
    panelData = [{} for _ in pathDictList]

    for xKey, yKey, xlabel, ylabel, fileTag in varPairs:

        isVelocityPair = fileTag == "Velocity"

        # --- determine shared axis limits across ALL study areas for this variable pair ---
        xAllValid = (
            np.concatenate([data[xKey][~np.isnan(data[xKey]) & ~np.isnan(data[yKey])] for data in allData])
            if allData
            else np.array([])
        )
        yAllValid = (
            np.concatenate([data[yKey][~np.isnan(data[xKey]) & ~np.isnan(data[yKey])] for data in allData])
            if allData
            else np.array([])
        )

        if xAllValid.size == 0:
            # e.g. gamma is only available if it is saved in the thalweg files
            log.info(f"No valid {xKey}/{yKey} data found, no {fileTag} regression plot is created.")
            continue

        if xAllValid.size > 0 and yAllValid.size > 0:
            sharedMin = np.nanmin([xAllValid.min(), yAllValid.min()])
            sharedMax = np.nanmax([xAllValid.max(), yAllValid.max()])
            margin = 0.05 * (sharedMax - sharedMin) if sharedMax > sharedMin else 1.0
            sharedMin -= margin
            sharedMax += margin
        else:
            sharedMin, sharedMax = 0.0, 1.0

        if isVelocityPair:
            allBoundaryVals = yVelBoundaries + xVelBoundaries
            sharedMax = max(sharedMax, max(allBoundaryVals) * 1.05)
            yEdges = [sharedMin] + yVelBoundaries + [sharedMax]
            xEdges = [sharedMin] + xVelBoundaries + [sharedMax]

        shadingEdges = (xEdges, yEdges, sizeColors) if isVelocityPair else None

        # --- one scatter + regression plot per study area ---
        for iArea, (pathDict, data, areaName) in enumerate(zip(pathDictList, allData, allNames)):
            x, y = data[xKey], data[yKey]
            mask = ~np.isnan(x) & ~np.isnan(y)
            x, y = x[mask], y[mask]
            panelArgs = (x, y, areaName, xlabel, ylabel, sharedMin, sharedMax, shadingEdges)

            # these pairs are plotted as panels of one figure (see below)
            if fileTag in panelTags:
                panelData[iArea][fileTag] = panelArgs
                continue

            fig, ax = plt.subplots()
            plotRegressionPanel(ax, *panelArgs)
            ax.set_title(f"{title} {areaName}".strip())

            simhashArea = pathDict["titleVariables"]["simHash"]
            sfx = zdSuffix if "Velocity" in fileTag else ""
            filename = f"ThalwegRegression_{fileTag}_{simhashArea}_{centerOf}{sfx}.png"
            fig.savefig(pathDict["savePath"] / filename)
            plt.close(fig)
            log.info(f"Saved {fileTag} regression plot as {pathDict['savePath'] / filename}")

        # --- combined plot: only the regression lines of all study areas, no scatter points ---
        figComb, axComb = plt.subplots()

        if isVelocityPair:
            _addSizeClassShading(axComb, yEdges, sizeColors, sharedMin, sharedMax, axis="y")
            _addSizeClassShading(axComb, xEdges, sizeColors, sharedMin, sharedMax, axis="x")

        for data, areaName in zip(allData, allNames):
            x, y = data[xKey], data[yKey]
            mask = ~np.isnan(x) & ~np.isnan(y)
            x, y = x[mask], y[mask]

            if len(x) < 2:
                log.info(f"Not enough data for {areaName} ({fileTag}) to fit a regression line.")
                continue

            coeffs = np.polyfit(x, y, 1)
            xFit = np.linspace(np.nanmin(x), np.nanmax(x), 100)
            axComb.plot(xFit, np.polyval(coeffs, xFit), zorder=4, label=f"{areaName} (n = {len(x)})")

        axComb.plot(
            [sharedMin, sharedMax], [sharedMin, sharedMax], "k:", linewidth=1, zorder=4, label="y = x"
        )

        axComb.set_xlim(sharedMin, sharedMax)
        axComb.set_ylim(sharedMin, sharedMax)
        axComb.set_aspect("equal", adjustable="box")

        axComb.set_xlabel(xlabel)
        axComb.set_ylabel(ylabel)
        axComb.set_title(f"{title} comparison of study areas".strip())
        axComb.legend()
        axComb.grid(True, zorder=0)

        sfx = zdSuffix if "Velocity" in fileTag else ""
        filenameComb = f"ThalwegRegression_{fileTag}_{simhashCombined}_{centerOf}{sfx}_comparison.png"
        figComb.savefig(savePath / filenameComb)
        plt.close(figComb)
        log.info(f"Saved combined {fileTag} regression plot as {savePath / filenameComb}")

    # --- one figure per study area with the panel pairs side by side ---
    for pathDict, areaName, panels in zip(pathDictList, allNames, panelData):
        tags = [tag for tag in panelTags if tag in panels]
        if len(tags) == 0:
            continue

        fig, axes = plt.subplots(1, len(tags), figsize=(6 * len(tags), 6), squeeze=False)
        for ax, tag in zip(axes[0], tags):
            plotRegressionPanel(ax, *panels[tag])
        fig.suptitle(f"{title} {areaName}".strip())
        fig.tight_layout()

        simhashArea = pathDict["titleVariables"]["simHash"]
        fileTag = "".join(tags)
        sfx = zdSuffix if "Velocity" in fileTag else ""
        filename = f"ThalwegRegression_{fileTag}_{simhashArea}_{centerOf}{sfx}.png"
        fig.savefig(pathDict["savePath"] / filename)
        plt.close(fig)
        log.info(f"Saved {fileTag} regression plot as {pathDict['savePath'] / filename}")


def plotRegressionPanel(ax, x, y, areaName, xlabel, ylabel, sharedMin, sharedMax, shadingEdges=None):
    """
    scatter plot of one study area with a linear regression line and a y = x reference line

    Parameters
    -----------
    ax: matplotlib axis
    x, y: numpy array
        data without nans
    areaName: str
        name of study area (used in the legend)
    xlabel, ylabel: str
        axis labels
    sharedMin, sharedMax: float
        shared axis limits (identical for x and y)
    shadingEdges: tuple or None
        (xEdges, yEdges, colors) for the size class shading (see _addSizeClassShading), None for no shading
    """
    if shadingEdges is not None:
        xEdges, yEdges, colors = shadingEdges
        _addSizeClassShading(ax, yEdges, colors, sharedMin, sharedMax, axis="y")
        _addSizeClassShading(ax, xEdges, colors, sharedMin, sharedMax, axis="x")

    ax.scatter(x, y, s=8, alpha=0.6, color="k", zorder=3, label=f"{areaName} (n = {len(x)})")

    if len(x) > 1:
        coeffs = np.polyfit(x, y, 1)
        xFit = np.linspace(np.nanmin(x), np.nanmax(x), 100)
        ax.plot(
            xFit,
            np.polyval(coeffs, xFit),
            "r--",
            zorder=4,
            label=f"fit: y = {coeffs[0]:.2f}x + {coeffs[1]:.2f}",
        )

    ax.plot([sharedMin, sharedMax], [sharedMin, sharedMax], "k:", linewidth=1, zorder=4, label="y = x")

    ax.set_xlim(sharedMin, sharedMax)
    ax.set_ylim(sharedMin, sharedMax)
    ax.set_aspect("equal", adjustable="box")

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend()
    ax.grid(True, zorder=0)


def _addSizeClassShading(ax, edges, colors, sharedMin, sharedMax, axis):
    """
    add background shading for size classes, clipped to the region below
    the y = x diagonal (same coloring style as the size class shading in
    plotBoxplot, but as a triangular area instead of a full axhspan/axvspan)

    Parameters
    -----------
    ax: matplotlib axis
    edges: list of float
        class boundaries including the outer axis limits, e.g.
        [sharedMin, b1, b2, b3, b4, sharedMax] -> 5 classes
    colors: list of str
        one color per class (len(edges) - 1 colors)
    sharedMin, sharedMax: float
        shared axis limits (identical for x and y, since aspect is "equal")
    axis: str
        "y" for horizontal bands (classes defined along the y-axis, shading
        fills from the left up to the diagonal), "x" for vertical bands
        (classes defined along the x-axis, shading fills from the bottom
        up to the diagonal)
    """
    if axis == "y":
        for i in range(len(edges) - 1):
            # only shade the region left of y = x (between x = sharedMin and x = y)
            yLow = np.clip(edges[i], sharedMin, sharedMax)
            yHigh = np.clip(edges[i + 1], sharedMin, sharedMax)
            if yHigh <= yLow:
                continue
            ax.fill(
                [sharedMin, yLow, yHigh, sharedMin],
                [yLow, yLow, yHigh, yHigh],
                color=colors[i],
                alpha=0.15,
                linewidth=0,
                zorder=1,
            )
    else:
        for i in range(len(edges) - 1):
            # only shade the region below y = x (between y = sharedMin and y = x)
            xLow = np.clip(edges[i], sharedMin, sharedMax)
            xHigh = np.clip(edges[i + 1], sharedMin, sharedMax)
            if xHigh <= xLow:
                continue
            ax.fill(
                [xLow, xHigh, xHigh, xLow],
                [sharedMin, sharedMin, xHigh, xLow],
                color=colors[i],
                alpha=0.15,
                linewidth=0,
                zorder=1,
            )
