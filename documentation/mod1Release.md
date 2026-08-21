# Module `mod1Release`

## Overview

The `mod1Release` module provides tools to delineate and prepare **potential release areas (PRAs)** as inputs for avalanche simulations.

The initial PRA delineation is implemented in [`praDelineationVeitinger.py`](#step-01-pradelineationveitinger) and can be run as a standalone script. The subsequent processing scripts clean, segment, classify, and convert the PRAs into FlowPy-ready inputs. To execute these post-processing steps as a complete pipeline, they are coordinated through one of the available workflow runners.

## Directory Modes

The `mod1Release` functions support two directory modes:

- **`avaDir`** represents a single AvaFrame-compatible scenario directory. This mode is used by the dynamic-parameterisation, AutoATES, and thalweg-analysis workflows.
- **`workFlowDir`** is a dictionary of paths used by `runAvaScenModelChain.py` to process multiple avalanche scenarios below `<workDir>/<project>/<ID>/`.

Not every `mod1Release` function supports both modes. Supporting a single-scenario `avaDir` mode directly in `runAvaScenModelChain.py` remains an open development task.

### Single-scenario Structure (`avaDir`)

A single-scenario workflow uses the following AvaFrame-compatible structure:

```text
<avaDir>/
├── Inputs/
│   ├── digital elevation model (*.tif or *.asc)
│   └── RES/ (or FOREST/)
│       └── forest raster (*.tif or *.asc)
├── Work/
│   ├── praProcessing/
│   ├── praSubcatchments/
│   ├── praSegmentation/
│   └── praPrepForFlowPy/
└── Outputs/
    └── PraDelineation/
```

### Multi-scenario Structure (`workFlowDir`)

`runAvaScenModelChain.py` initializes the multi-scenario project structure using `runAvaScenModelChainCfg.ini`:

```ini
[MAIN]
initWorkDir = True

[WORKFLOW]
runAllPRASteps = True
```

`initWorkDir` creates the project directories, while `runAllPRASteps` executes all active PRA-processing steps. Individual steps can instead be enabled separately in `[WORKFLOW]`.

The initialized paths are stored in the `workFlowDir` dictionary:

```text
<workDir>/<project>/<ID>/
├── 00_input/
├── 01_praDelineation/
├── 02_praSelection/
├── 03_praBottleneckSmoothing/      # initialized but currently not executed
├── 04_praSubcatchments/
├── 05_praProcessing/
├── 06_praSegmentation/
├── 07_praAssignElevSize/
├── 08_praPrepForFlowPy/
└── 09_flowPyBigDataStructure/
    └── <PRA-case>/
        └── SizeN/
            └── dry|wet/
                └── Inputs/
```

The unused `03_praBottleneckSmoothing/` directory explains why the physical folder prefixes after PRA selection are one number higher than the active processing-step numbers.

Step 08 expands each PRA case into different size classes and dry/wet flow regimes. Each `SizeN/<flow-regime>/` directory becomes an independent AvaFrame-compatible scenario for subsequent mobility parameterisation and FlowPy simulation.

## Workflow Runners

The following workflows use `mod1Release`:

| Workflow runner | `mod1Release` steps used | Directory mode |
|---|---|---|
| `runAvaScenModelChain.py` | **01** `praDelineationVeitinger` → **02** `praSelection` → **03** `praSubCatchments` → **04** `praProcessing` → **05** `praSegmentation` → **06** `praAssignElevSize` → **07** `praPrepForFlowPy` → **08** `praMakeBigDataStructure` | `workFlowDir` |
| `runDynamicParameterisation.py` | **01** `praDelineationVeitinger` → **04** `praProcessing` → **03** `praSubCatchments` → **05** `praSegmentation` → **07** `praPrepForFlowPy` | `avaDir` |
| `runAutoAtesModelChain.py` | **01** `praDelineationVeitinger` → **04** `praProcessing` → **03** `praSubCatchments` → **05** `praSegmentation` → **07** `praPrepForFlowPy` | `avaDir` |
| `runThalwegAnalysis.py` | Optional release preparation: **01** `praDelineationVeitinger` → **04** `praProcessing` → **03** `praSubCatchments` → **05** `praSegmentation` → **07** `praPrepForFlowPy` | `avaDir` |

There is currently no dedicated runner for the complete `mod1Release` pipeline. It is executed through one of the workflows listed above.

---

## Step 01: `praDelineationVeitinger`

`praDelineationVeitinger` delineates potential release areas from slope, wind shelter, terrain ruggedness, and the optional influence of forest cover. These indicators are derived from a digital elevation model (DEM).

The method follows a **fuzzy-logic approach**: each raster cell is assigned a continuous degree of membership representing how likely it is to be part of a potential release area.

The algorithm was developed by [Veitinger et al. (2016)](https://nhess.copernicus.org/articles/16/2211/2016/) and extended by [Sharp (2018)](https://doi.org/10.13140/RG.2.2.18673.94567). The implementation follows this approach with minor modifications, including:

- a Numba-parallelized wind-shelter calculation to improve computational performance;
- support for both `avaDir` and `workFlowDir`;
- integration into the AvaFrame-compatible input and output structure.

The original implementation is available in this [repository](https://github.com/jocha81/Avalanche-release). Refer to the publications above for details about the underlying method.

### Input Files

The algorithm requires a DEM and, optionally, a forest raster. In `avaDir` mode, they are read from:

```text
<avaDir>/
└── Inputs/
    ├── digital elevation model (*.tif or *.asc)
    └── RES/ (or FOREST/)
        └── forest raster (*.tif or *.asc)
```

### Output Files

In `avaDir` mode, the results are written to:

```text
<avaDir>/
└── Outputs/
    └── PraDelineation/
        ├── pra.tif
        ├── pra_binary_th<NNN>.tif
        ├── slope.tif
        ├── aspect.tif
        └── additional intermediate rasters
```

`pra.tif` contains the continuous PRA membership values. The `pra_binary_th<NNN>.tif` files contain the corresponding binary release masks for the configured threshold or thresholds.

Default parameters are defined in `praDelineationVeitingerCfg.ini` and can be adjusted in `local_praDelineationVeitingerCfg.ini`. Workflow-specific values can also be overridden:

- under `[praDELINEATION]` in `runAvaScenModelChainCfg.ini`;
- under `[mod1Release_praDelineationVeitinger_override]` in the `avaDir` workflow configuration files.

---

## PRA Processing Steps

The following scripts convert the delineated PRAs into polygon and raster inputs for `AvaFrame::com4FlowPy`.

The complete `workFlowDir` workflow runs Steps 01–08. The simplified `avaDir` workflows use **01 → 04 → 03 → 05 → 07**, skipping PRA selection, elevation and size assignment, and creation of the multi-scenario structure.

Shared processing parameters are defined in `(local_)mod1ReleaseCfg.ini`. They can also be overridden in the corresponding workflow configuration files.

### Step 02: `praSelection` *(workFlowDir only)*

`praSelection` converts the continuous PRA raster from Step 01 into binary release masks using:

- a PRA probability threshold;
- minimum and maximum elevation;
- selected aspect sectors;
- an optional project-region mask.

**Output:** One binary PRA raster for each selected aspect sector, for example `pra030secS.tif`.

### Step 03: `praSubCatchments`

`praSubCatchments` derives hydrologically meaningful subcatchments from the DEM using WhiteboxTools. The resulting subcatchments are smoothed and subsequently used to divide the PRA polygons into terrain-related units.

This step supports both directory modes.

**Output:** Subcatchment rasters and vector files containing the original and smoothed subcatchments.

### Step 04: `praProcessing`

`praProcessing` checks the PRA raster metadata against the DEM and cleans the binary release masks using two neighbourhood filters:

1. Cells without enough direct neighbours are removed.
2. Cells without enough diagonal neighbours are removed.

The cleaned rasters are then polygonized, and polygon areas and temporary IDs are added.

In `avaDir` mode, the binary raster from Step 01 is processed directly. In `workFlowDir` mode, the selected raster from Step 02 is used.

**Output:** Cleaned PRA rasters (`*_BnCh1.tif` and `*_BnCh2.tif`) and polygonized PRA GeoJSON files.

### Step 05: `praSegmentation`

`praSegmentation` intersects the cleaned PRA polygons from Step 04 with the smoothed subcatchments from Step 03. This divides the PRAs into hydrologically meaningful segments.

The area of each segment is calculated, and segments smaller than the configured `sizeFilter` are removed.

This step supports both directory modes.

**Output:** Segmented PRA GeoJSON files and size-filtered files ending in `_sizeF<sizeFilter>.geojson`.

### Step 06: `praAssignElevSize` *(workFlowDir only)*

`praAssignElevSize` enriches the segmented PRA polygons with:

- minimum, maximum, and mean elevation;
- an elevation-band classification;
- a size class based on the PRA area;
- optional administrative-region metadata.

**Output:** Enriched PRA GeoJSON files ending in `-ElevBands-Sized.geojson`.

### Step 07: `praPrepForFlowPy`

`praPrepForFlowPy` prepares the PRA polygons for FlowPy by:

1. grouping them by elevation band and size class;
2. assigning unique PRA IDs;
3. rasterizing the configured PRA attributes and IDs;
4. optionally deriving boundary-only rasters.

In `avaDir` mode, Step 06 is normally skipped and the size-filtered Step 05 output is used directly. The calling workflow subsequently copies the required files into `Inputs/REL`, `Inputs/RELArea`, `Inputs/RELID`, and, where required, `Inputs/RELJSON`.

**Output:** FlowPy-ready GeoJSON and raster files, together with `praID_translation.csv`.

### Step 08: `praMakeBigDataStructure` *(workFlowDir only)*

`praMakeBigDataStructure` creates the multi-scenario structure described above. Each PRA case is expanded into the configured avalanche sizes and the `dry` and `wet` flow regimes.

The prepared release rasters and vectors are copied into the corresponding `REL`, `RELArea`, `RELID`, and `RELJSON` input folders. Each resulting `SizeN/<flow-regime>/` directory can then be processed as an independent FlowPy scenario.

**Output:**

```text
09_flowPyBigDataStructure/
└── <PRA-case>/
    └── SizeN/
        └── dry|wet/
            └── Inputs/
                ├── REL/
                ├── RELArea/
                ├── RELID/
                └── RELJSON/
```

---

Go back to [main documentation](../README.md).
