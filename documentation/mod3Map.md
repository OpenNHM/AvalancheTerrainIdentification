# Module `mod3Map`

## Overview

The `mod3Map` module provides tools to map and classify terrain.

## `autoATESClassifier`

The `autoATESClassifier` classifies terrain into the four **Avalanche Terrain Exposure Scale (ATES)** classes,
`simple`, `challenging`, `complex` and `extreme`, based on slope angle, potential release areas (PRA), avalanche runout
(Flow-Py travel angle) and, optionally, forest density and forest interaction.

The autoATES v2.0 classifier was developed
by [Toft et al. (2023a)](https://doi.org/10.5194/nhess-2023-114); [Toft et al. (2023b)](https://github.com/AutoATES/AutoATES-v2.0/tree/main);
the implementation here follows that approach with minor modifications. For details on the underlying method, refer to
the two publications above.

### Modified Workflow

Compared to the publications mentioned above, we made the following changes (described in more detail in Hesselbach
(2023)[^1], [Huber et al. (2023)](https://arc.lib.montana.edu/snow-science/objects/ISSW2023_P2.48.pdf) and Spannring
(2024)[^2]):

- No overhead hazard is considered.
- Forest interaction: if a Flow-Py forest-interaction raster is available, it indicates how many forested cells an
  avalanche path has passed through. The autoATES classifier reclassifies cells, which are assigned to forest
  interaction value of `FORESTINT1` or higher, to a lower class. If a cell has a value higher than `FORESTINT2`, ATES
  class 3 is reclassified to ATES class 1.

### Input Files

The algorithm requires a digital elevation model, potential release areas (binary format), avalanche travel angle (in
°), and, optionally, a forest density layer and a forest-interaction layer. If `customPaths` is `True`, the paths to the
respective files are provided directly in the configuration file. If `customPaths` is `False`, the Inputs must follow
this folder structure:

```text
<avaDir>/
└── Inputs/
    ├── digital elevation model (*.tif or *.asc)
    ├── REL
    │   └── PRA raster (*.tif or *.asc)
    └── RES/ or FOREST/
        └── forest density raster (*.tif or *.asc; optional)
└── Outputs/
    └── com4FlowPy/
        └── peakFiles/
            └── res_<flowpyHash>/
                ├── travel-angle raster, filename contains "fpTravelAngleMax" (*.tif)
                └── forest-interaction raster, filename contains "forestInteraction" (*.tif; optional)            
```

Configuration parameters can be adjusted in `(local_)autoATESClassifierCfg.ini`.

### Output Files

The resulting ATES layer, together with intermediate results, is written to the `Outputs/autoATES` folder:

```text
<avaDir>/
└── Outputs/
    └── autoATES/
        ├── ates_gen.tif
        └── ...
```

---

## Regional Thalweg Analysis

The **regional thalweg analysis** tools visualize and statistically summarize simulated avalanche "thalwegs" e.g.,
derived from [AvaFrame::com4FlowPy]([AvaFrame::com4FlowPy](https://docs.avaframe.org/en/latest/moduleCom4FlowPy.html#))
results. A thalweg is the central flow line (main direction) of a simulated avalanche path. These analyses can be used
to compare the avalanche terrain of various study areas and to represent the avalanche terrain two-dimensionally (e.g.,
see [Spannring et al. 2026](https://meetingorganizer.copernicus.org/EGU26/EGU26-10580.html)).

The tools produce three kinds of output:

- **2D representation** of an individual thalweg
- **map of thalwegs** of all thalwegs, overlaid on the DEM and a chosen simulation-result raster.
- [**AIMEC-style altitude/velocity
  plots**](https://docs.avaframe.org/en/latest/moduleAna3AIMEC.html#analysis-on-simulation-level-plots) along a thalweg.
- **Regional statistics** (boxplots and scatter plots) summarizing a chosen variable (e.g. velocity, impact pressure,
  travel length, release area) across *all* simulated thalwegs, optionally classified by avalanche size class.

### Steps

For a given avalanche directory and simulation (`simhash`), `regionalThalweg2DPlotMain` performs the following steps:

1. Determines which thalweg (s) to plot:

- a single thalweg selected by `startRow`/`startCol` (a specific starting cell), **or**
- a single thalweg selected by `relId` (a specific release-area ID), **or**
- all thalwegs found for a given `centerOfVariable`, **or**
- all thalwegs for every available "center of" variant, if `centerOfVariable` is left empty.

2. Loads the corresponding pre-computed thalweg data (`.pickle` files, from `Outputs/<module>/peakFiles/
   res_<simhash>/thalwegData`), and derives an extended and resampled profile
   via [AvaFrame's::preparePathGeneralMain](https://docs.avaframe.org/en/latest/moduleAna5Utils.html) and saves the
   extended profile (prefixed `extended_`) alongside the original pickle file.
3. Generates the plots enabled via the `[FLAGS]` configuration (see below).

 
---

## Plot Types

| Flag                       | Function                             | Description                                                                                                                                                                                                                                                                |
|----------------------------|--------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `plotThalweg2D`            | `plotThalweg2D`                      | Two-panel figure: a map of the DEM/hillshade with a chosen result raster (`plotVariable`) and the thalweg(s) drawn on top; below it, a longitudinal elevation profile annotated with the input `alpha` angle, the effective runout angle, and the velocity along the path. |
| `plotThalwegAltitude`      | `plotDFAThalwegAltitude`             | AIMEC-style velocity/thickness-along-thalweg plot, via AvaFrame's `outAIMEC.plotVelThAlongThalweg`.                                                                                                                                                                        |
| `plotThalwegLocation`      | `plotDFAGenerationLocation`          | Plots the DFA path-generation raster (default `fpTravelAngleMax`) together with the DEM and the thalweg profile, to visualize where and why the thalweg was generated.                                                                                                     |
| `plotAllThalwegLocations`  | `plotThalweg2D(..., onlyField=True)` | Same as `plotThalweg2D`, but only the map panel (all thalweg locations), without a profile plot.                                                                                                                                                                           |
| `plotStatisticBoxplot`     | `plotBoxplot`                        | Boxplot/violin plot of a chosen statistic (`statisticVariable`) across all thalwegs, with avalanche-size-class background shading.                                                                                                                                         |
| `plotStatisticScatterPlot` | `plotScatterInputEffective`          | Scatter plot comparing the input (model parameter) vs. effective (simulated) maximum velocity across all thalwegs.                                                                                                                                                         |

---

## Input Files

```text
<avaDir>/
├── Inputs/
│   ├── DEM.tif or DEM.asc
│   └── RELJSON/
│       └── release-area polygon (*.shp or *.geojson; optional, for overlay)
└── Outputs/
    └── <modName>/
        └── peakFiles/
            └── res_<simhash>/
                ├── <result rasters> (e.g. zdelta, flux, fpTravelAngleMax, cellCounts)
                └── thalwegData/
                    └── thalwegData_<centerOf>_<relId or startRow_startCol>.pickle
```

## Output Files

All plots are saved to `Outputs/regionalThalwegPlot`:

```text
<avaDir>/
└── Outputs/
    └── regionalThalwegPlot/
        └── thalweg analysis plots (*.png)
```

The extended thalweg profiles (`extended_thalwegData_*.pickle`) are saved alongside the original pickle files in
`thalwegData/`.

---

[^1]: Hesselbach, C., 2023: Adaptation and Application of an Automated Avalanche Terrain Classification in Austria.
Masters’ Thesis, Universität für Bodenkultur, Wien.

[^2]: Spannring., P., 2024: Comparison of two avalanche terrain classification approaches:
Avalanche Terrain Exposure Scale - Classified Avalanche Terrain. Masters’ Thesis, University of Innsbruck.

---

Go back to [main documentation](../README.md).