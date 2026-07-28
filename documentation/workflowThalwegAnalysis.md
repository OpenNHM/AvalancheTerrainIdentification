# Workflow: Thalweg Analysis

## Overview

The **thalweg analysis workflow** (`workflows/runThalwegAnalysis.py`) runs a full avalanche simulation chain and then
analyzes and visualizes the resulting flow paths ("thalwegs") with the
[regional thalweg analysis](mod3Map.md#regional-thalweg-analysis) tools. It can either:

- run the full chain: PRA delineation and preparation, dynamic mobility parameterization, and
  `AvaFrame::com4FlowPy`, and then analyze the resulting simulation, **or**
- skip straight to the thalweg analysis of an **existing** `com4FlowPy` result.

Which of the two is used is controlled by the `runFlowPy` flag in the configuration file.

The workflow is implemented in `workflows/runThalwegAnalysis.py`.

---

## Workflow Steps

### 1. PRA Delineation, Parameterization and Mobility Simulation (if `runFlowPy = True`)

If `runFlowPy` is `True`, the workflow runs the following steps to prepare and execute an avalanche simulation, before
analyzing its results in Step 2:

1. **PRA delineation**: [`mod1Release`](mod1Release.md#pradelineationveitinger):
   `praDelineationVeitinger.runPraDelineation` derives raw
   potential release areas from the DEM (and, optionally, a forest mask).
2. **PRA processing (polygonizing)**: [`mod1Release`](mod1Release.md): `praProcessing.runPraProcessing` converts the raw
   PRA raster into polygons.
3. **Subcatchments**: [`mod1Release`](mod1Release.md): `praSubCatchments.runSubcatchments` derives subcatchments used to
   structure the release areas.
4. **PRA segmentation**: [`mod1Release`](mod1Release.md): `praSegmentation.runPraSegmentation` segments the polygons
   into individual, distinct release areas.
5. **PRA rasterization**: [`mod1Release`](mod1Release.md): `praPrepForFlowPy.runPraPrepForFlowPy` rasterizes the
   segmented release areas back to grids, writing a release-ID raster (`*-5-praID.tif`), a release-area raster
   (`*-5-praAreaM.tif`) and a release-area polygon (`*-5.geojson`).
6. **Dynamic mobility parameterization**: [
   `mod2Mobility`](mod2Mobility.md#computeandsaveparameters--deriving-the-mobility-parameters):
   `compParams.computeAndSaveParameters` computes the mobility parameters `alpha`, `umax` and `exp` for each release
   area, saved to `Inputs/ALPHA`, `Inputs/UMAX` and `Inputs/EXP`.
7. **Avalanche simulation**: [
   `AvaFrame::com4FlowPy`]([AvaFrame::com4FlowPy](https://docs.avaframe.org/en/latest/moduleCom4FlowPy.html#)), via
   `runCom4FlowPy.main`.

The rasters and polygon generated in Step 5 are copied into the `Inputs` folder structure expected by the downstream
steps and by the thalweg analysis:

| Generated file                                         | Copied to                   |
|--------------------------------------------------------|-----------------------------|
| `*-5-praID.tif`                                        | `Inputs/RELID`              |
| `*-5-praAreaM.tif`                                     | `Inputs/RELArea`            |
| `*-5.geojson`                                          | `Inputs/RELJSON`            |
| binarized `*-5-praAreaM.tif` (values `> 0` set to `1`) | `Inputs/REL/pra_binary.tif` |

> **Note:** as in the other workflows, if a matching file already exists in `Inputs/REL`, `Inputs/RELID`,
> `Inputs/RELArea` or `Inputs/RELJSON`, the corresponding copy step is skipped and the existing file is used
> instead.

If `runFlowPy = False`, this entire step is skipped, and the workflow proceeds directly to Step 2 using existing
simulation results.

### 2. Thalweg Analysis

Uses [regional thalweg analysis documentation](mod3Map.md#regional-thalweg-analysis).

`regionalThalwegAnalysis.regionalThalweg2DPlotMain` is called with the `com4FlowPy` result, generating the thalweg
analyses plots.

---

## Configuration

The following override sections of `runThalwegAnalysisCfg.ini`
override the default configurations of each submodule:

| Override section                               | Applies to                                                                 |
|------------------------------------------------|----------------------------------------------------------------------------|
| `mod1Release_praDelineationVeitinger_override` | `praDelineationVeitinger` (PRA delineation)                                |
| `mod1Release_mod1Release_override`             | `mod1Release` (PRA processing, subcatchments, segmentation, rasterization) |
| `mod2Mobility_compParams_override`             | `compParams` (mobility parameterization)                                   |
| `com4FlowPy_com4FlowPy_override`               | `AvaFrame::com4FlowPy` (FlowPy mobility simulation)                        |
| `mod3Map_regionalThalwegAnalysis_override`     | `regionalThalwegAnalysis` (thalweg plots and statistics)                   |

Each override section has a `defaultConfig` flag: if `True`, the sub-module's own default configuration is used as the
base configuration, with the parameter values given in `runThalwegAnalysisCfg.ini` applied on top as overrides. If
`False`, and a `local_` configuration file for that sub-module is available, that local configuration is used instead.

As with `atiCfg.ini`, create a `local_runThalwegAnalysisCfg.ini` copy to adjust these settings for your own run. See
the [regional thalweg analysis documentation](mod3Map.md#regional-thalweg-analysis) for the
settings controlling the thalweg plots themselves.

---

## Input Files

If `runFlowPy = True`, at minimum, the workflow requires a DEM. A forest raster (values between 0 and 1) is optional
and, if provided, is used both for PRA delineation (`mod1Release`) and for the avalanche mobility simulation. that is
provided in the following structure:

```text
<avaDir>/
└── Inputs/
    ├── DEM.tif or DEM.asc
    └── RES/ or FOREST/
        └── forest density raster (*.tif or *.asc; optional)
```

If `runFlowPy = False`, an existing `com4FlowPy` result (including its `thalwegData`) must already be present under
`Outputs/com4FlowPy/peakFiles/res_<hash>`.

## Output Files

```text
<avaDir>/
├── Inputs/
│   ├── REL/, RELID/, RELArea/, RELJSON/   # PRA rasters and polygon (Step 1)
│   └── ALPHA/, UMAX/, EXP/                # mobility parameters (Step 1)
├── Outputs/
│   ├── PraDelineation/                    # raw PRA delineation (Step 1)
│   ├── com4FlowPy/
│   │   └── peakFiles/
│   │       └── res_<FlowPyHash>/          # com4FlowPy simulation + thalweg data (Step 1)
│   └── regionalThalwegPlot/               # thalweg plots and statistics (Step 2)
└── Work/
    └── praPrepForFlowPy/                  # intermediate PRA rasterization files (Step 1)
```

---

## How to Run

For now, you also need to clone the [AvaFrame repository](https://github.com/OpenNHM/AvaFrame) in the same directory as
`AvaScenarioModelChain`, and check out the `PS_FP_thalweg` branch:

```bash
git clone https://github.com/OpenNHM/AvaFrame.git
cd [YOURDIR]/AvaFrame
git checkout PS_FP_thalweg
cd ../AvaScenarioModelChain
pixi shell --environment dev
python workflows/runThalwegAnalysis.py
```

See the main [README](../README.md) for full installation and setup instructions.

---

## Notes

- The authoritative source for the exact workflow logic is the implementation in
  `workflows/runThalwegAnalysis.py`.
- For details on the individual processing steps, refer to the module documentation:
  [`mod1Release`](mod1Release.md), [`mod2Mobility`](mod2Mobility.md),
  [regional thalweg analysis](mod3Map.md).