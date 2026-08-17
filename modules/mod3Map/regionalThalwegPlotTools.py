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
        "": "",
    }
    if variable == "velocityMax":
        variableOut = "zdelta"
    else:
        variableOut = variable
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
    dataConstrained = raster[rowsMin: rowsMax + 1, colsMin: colsMax + 1]
    demConstrained = dem[rowsMin: rowsMax + 1, colsMin: colsMax + 1]
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

    (extentCellCenters, extentCellCorners, rowsMinPlot, rowsMaxPlot, colsMinPlot, colsMaxPlot) = (
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
    dataThalweg: dict
        profile of thalweg that is highlighted here

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
        zDeltaMax (float or int): input parameter of the simulation: zDelta Maximum threshold
    pathDict: dict
        contains paths
    centerOf: str
        which center of is used (possible: '' (default),'CoE', 'CoZd', 'CoF')

    Returns
    -----------
    ax: matplotlib axis
        Axis containing the thalweg plot
    """
    # demDict = gI.readDEM(pathDict["avalancheDir"])
    # dem = demDict["rasterData"]
    # header = demDict["header"]
    # cellSize = header["cellsize"]

    x = np.array(dataThalweg["x"])
    y = np.array(dataThalweg["y"])
    z = np.array(dataThalweg["z"])
    s = np.array(dataThalweg["s"])
    zdelta = dataThalweg["zdelta"]
    sExtended = np.array(dataThalweg["s"])
    zExtended = np.array(dataThalweg["z"])
    indStart = dataThalweg["indStartMassAverage"]
    indEnd = dataThalweg["indEndMassAverage"]

    # file = getRasterFile(pathDict["pathToOutput"], variable="zdelta")
    # zdelta = getThalwegValuesFromRaster(file, x, y)

    _, indInPath = tools.getProfileInPath(pathDict["pathToOutput"], dataThalweg)

    maskNan = np.ones(zdelta.shape, dtype=bool)
    maskNan[indInPath] = False
    zdelta[maskNan] = np.nan
    s[maskNan] = np.nan
    z[maskNan] = np.nan

    # get FlowPy input parameter
    if "alpha" in dataThalweg.keys():
        alpha = dataThalweg["alpha"]
        exp = dataThalweg["exponent"]
        zDeltaMax = dataThalweg["zDeltaMax"]
    else:
        alpha = None
        exp = None
        zDeltaMax = None

    s_max = s[zdelta == np.nanmax(zdelta)]
    z_max = z[zdelta == np.nanmax(zdelta)]
    zdelta_max = zdelta[zdelta == np.nanmax(zdelta)]

    # calculate effective runout angle
    angle_rad = np.arctan((np.nanmax(z) - np.nanmin(z)) / (np.nanmax(s) - np.nanmin(s)))
    angle_degrees = np.rad2deg(angle_rad)

    ds = np.nanmax(s) - np.nanmin(s)
    dh = ds * np.tan(np.deg2rad(alpha))

    ax.hlines(
        np.nanmax(z) - dh, ds * 0.85, s[indInPath[0]] + ds, colors="k", linestyles="dotted", linewidths=0.7
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
        sExtended[indStart: indEnd + 1],
        zExtended[indStart: indEnd + 1],
        "-y.",
        label="z",
        lw=2,
        path_effects=[pe.Stroke(linewidth=3, foreground="k"), pe.Normal()],
    )
    l = ax.legend(handles=[dummyGeom, thalweg, thalwegTop, thalwegBot], loc="upper center")
    ax.add_artist(l)
    # dummy for legend group
    (p1,) = ax.plot(np.nan, np.nan, linestyle="none", label="Model input\nparameter")
    (p2,) = ax.plot(
        [s[indInPath[0]], ds + s[indInPath[0]]],
        [np.nanmax(z), np.nanmax(z) - dh],
        "k--",
        linewidth=0.7,
        label=rf"""$\alpha_{{input}}$ = {np.round(alpha, 1)}°""" if alpha is not None else "",
    )
    # dummy for legend group
    (p3,) = ax.plot(np.nan, np.nan, linestyle="none", label="Model results &\nderived metrics")
    (p4,) = ax.plot(s, [d + z for d, z in zip(z, zdelta)], "r", lw=2, label="$z^{vel}$")
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
        label="$v_{max}$ = " + str(np.round(np.sqrt(zdelta_max[0] * 2 * 9.81), 1)) + " m/s",
    )
    (p6,) = ax.plot(
        [s[indInPath[0]], s[-1]],
        [z[indInPath[0]], z[-1]],
        color="lightgrey",
        linestyle="--",
        linewidth=1,
        label=rf"""$\alpha_{{eff}}$ = {np.round(angle_degrees, 1)}°""",
    )

    (p7,) = ax.plot(
        [s[indInPath[0]], s[indInPath[-1]]],
        [np.nanmin(z)] * 2,
        color="grey",
        linewidth=1,
        linestyle="--",
        label=rf"""$\Delta$s = {np.round(s[indInPath[-1]] - s[indInPath[0]], 1)} m""",
    )
    p8 = ax.vlines(
        x=s[indInPath[0]],
        ymin=z[indInPath[-1]],
        ymax=z[indInPath[0]],
        color="silver",
        linestyle="--",
        linewidth=1,
        label=(rf"$\Delta z = {np.round(z[indInPath[0]] - z[indInPath[-1]], 1)}$ m"),
    )

    # ax.text(s_max[0] + 1, z_max[0] + zdelta_max[0]/2, '$v_{max}$ = ' + str(np.round(np.sqrt(zdelta_max[0] * 2 * 9.81),1)) + ' m/s', va = 'center')
    # ax.text((max(s)/5*4), min(z) + (max(z) - min(z)) / 22, fr'{angle_degrees:.1f}°', fontsize=11, ha='center')
    # ax.text((ds*0.88), (max(z)-dh) * 1.05, fr'{alpha:.1f}°', fontsize=11, ha='center')
    ax.set(xlabel="Horizontal distance [m]")
    ax.set(ylabel="Elevation [m]")
    ax.legend(handles=[p1, p2, p3, p4, p5, p6, p7, p8], loc="upper right")  # , bbox_to_anchor=(1, 1))

    '''
    ax.text(
        max(s) * 0.5,
        max(z) * 0.95,
        (
            f"""model parameters: \n alpha: {alpha}° \n exp: {np.round(exp, 1)} \n $Z^{{vel}}_{{max}}$: {np.round(zDeltaMax, 1)} m \n $v_{{max}}$: {round(np.sqrt(zDeltaMax * 2 * 9.81), 1)} m/s"""
            if alpha is not None
            else ""
        ),
        va="top",
        ha="left",
    )'''

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
    ylabel = tools.getYlabelBoxplot(varName)

    # --- collect data + labels for every study area ---
    dataList = []
    labels = []
    for pathDict in pathDictList:
        path = pathDict["pathToOutput"]
        dataNan = tools.getDataBoxplots(path, varName, centerOf, cfgGen.getfloat("rho"))
        data = np.delete(dataNan, np.where(np.isnan(dataNan)))
        dataList.append(data)
        areaName = pathDict.get("studyAreaName", pathDict["titleVariables"]["simHash"])
        print(areaName, " : ", np.nanmedian(data))
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

    if cfgGen["boxplotYlimMin"] == "":
        cfgGen["boxplotYlimMin"] = "0"
    if cfgGen["boxplotYlimMax"] != "":
        ax2.set_ylim([cfgGen.getfloat("boxplotYlimMin"), cfgGen.getfloat("boxplotYlimMax")])

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

    if varName == "alphaIn":
        ax2.set_ylim([19, 36])
    if varName in ["velocityIn", "velocity"]:
        ax2.set_ylim([-1, 50])

    plt.ylabel(ylabel, fontsize=13)
    if title == "" and len(pathDictList) == 1:
        title = f"thalwege {centerOf}"
    plt.title(title)
    plt.grid(True)

    # --- save: combine info from all study areas ---
    savePath = pathDictList[0]["savePath"]
    simhashCombined = "-".join(pd["titleVariables"]["simHash"] for pd in pathDictList)
    filename = f"ThalwegStatistic_{simhashCombined}_{varName}_{centerOf}.png"
    fig.savefig(savePath / filename)
    log.info(f"Saved boxplot path as {savePath / filename}")


def plotScatterInputEffective(pathDict, cfg, title=""):
    """
    shows and potentially saves Violinplot and Boxplot

    Parameters:
    -----------
    path: str
        OutputPath of the FlowPy simulation
    dataNan: np.array
        data that is analysed and plotted (can contain nans)
    title: str
        title for the plot
    """
    path = pathDict["pathToOutput"]
    cfgGen = cfg["GENERAL"]
    cfgSize = cfg["SIZECLASS"]
    varName = cfgGen.get("statisticVariable")
    centerOf = cfgGen.get("centerOfVariable")

    if varName in ["velocity", "velocityMaxIn", "velocityAveraged"]:
        # dataNanIn = getDataBoxplots(path, "velocityIn", centerOf)
        # dataNanEff = getDataBoxplots(path, "velocity", centerOf)
        # TODO: think of a better way!
        dataDict = tools.maxParameterOfAllThalwegs(path, ["test"], centerOf)
        dataNanIn = dataDict["velocityIn"]
        # dataNanEff = zDelta2velocity(np.array(dataDict["zdelta"]))
        dataNanEff = dataDict["velocity"]

    else:
        return

    fig, ax2 = plt.subplots()  # figsize = [4,5])
    # fig.tight_layout()
    labels = [f" (n = {len(dataNanEff)})"]

    ax2.scatter(dataNanIn, dataNanEff, s=0.4)
    maxlim = np.nanmax([dataNanIn, dataNanEff])

    ax2.plot([0, maxlim + 5], [0, maxlim + 5], c="k", linestyle="--")

    # Color background
    if varName in ["travelLengthMax", "impressure"]:
        ysize1Max = cfgSize.getint(f"{varName}Size1Max")
        ysize2Max = cfgSize.getint(f"{varName}Size2Max")
        ysize3Max = cfgSize.getint(f"{varName}Size3Max")
        ysize4Max = cfgSize.getint(f"{varName}Size4Max")
        y_min, y_max = ax2.get_ylim()
        y_max = np.max([y_max, 1.1 * ysize4Max])
        ax2.axhspan(0, ysize1Max, facecolor="#" + cfgSize["colorSize1"], alpha=0.2)  # Avalanche size 1
        ax2.axhspan(
            ysize1Max,
            ysize2Max,
            facecolor="#" + cfgSize["colorSize2"],
            alpha=0.2,
        )  # size 2
        ax2.axhspan(
            ysize2Max,
            ysize3Max,
            facecolor="#" + cfgSize["colorSize3"],
            alpha=0.2,
        )  # size 3
        ax2.axhspan(
            ysize3Max,
            ysize4Max,
            facecolor="#" + cfgSize["colorSize4"],
            alpha=0.2,
        )  # size 4
        ax2.axhspan(ysize4Max, y_max, facecolor="#" + cfgSize["colorSize5"], alpha=0.2)  # size 5

        # if varName == "impressure":
        #    class_lab = "$C_{ip}$"
        # elif varName == "path_area":
        #   class_lab = "$B_{aa}$"
        # elif varName == "travelLengthMax":
        #    class_lab = "$E_{rl}$"
        # else:
        #    class_lab = ""
        class_lab = ""

        ax2.text(
            1.5,
            0 + (ysize1Max * 0.75),
            f"{class_lab} 1",
            ha="center",
            va="center",
            color="#008B8B",
            fontsize=13,
        )
        ax2.text(
            1.5,
            ysize1Max + (ysize2Max - ysize1Max) / 2,
            f"{class_lab} 2",
            ha="center",
            va="center",
            color="#4682B4",
            fontsize=13,
        )
        ax2.text(
            1.5,
            ysize2Max + (ysize3Max - ysize2Max) / 2,
            f"{class_lab} 3",
            ha="center",
            va="center",
            color="#6495ED",
            fontsize=13,
        )
        ax2.text(
            1.5,
            ysize3Max + (ysize4Max - ysize3Max) / 2,
            f"{class_lab} 4",
            ha="center",
            va="center",
            color="#CD5C5C",
            fontsize=13,
        )
        ax2.text(
            1.5,
            ysize4Max + (y_max - ysize4Max) / 2,
            f"{class_lab} 5",
            ha="center",
            va="center",
            color="#B22222",
            fontsize=13,
        )
        ax2.set_yticks([ysize1Max, ysize2Max, ysize3Max, ysize4Max])
        ax2.set_yticklabels([ysize1Max, ysize2Max, ysize3Max, ysize4Max], fontsize=13)

    if varName == "alphaIn":
        ax2.set_ylim([19, 36])
    if varName in ["velocityMaxIn", "velocity", "velocityAveraged"]:
        ax2.set_ylim([-1, 60])
        plt.ylabel("effective max. velocity [m/s]", fontsize=13)
        plt.xlabel("input (model parameter) max. velocity [m/s]", fontsize=13)

    if title == "":
        title = f"thalwege {centerOf}"
    plt.title(title)
    plt.grid(True)
    savePath = pathDict["savePath"]
    simhash = pathDict["titleVariables"]["simHash"]
    filename = f"ThalwegScatter_{simhash}_{varName}_{centerOf}.png"
    fig.savefig(savePath / filename)
    log.info(f"Saved boxplot path as {savePath / filename}")


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
