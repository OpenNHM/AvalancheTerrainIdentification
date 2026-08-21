## Avalanche Terrain Identification (ATI)


<p align="center">
  <img src="https://media.giphy.com/media/3Xzlefv57zcrVIPPRN/giphy.gif" 
       alt="Avalanche Scenario Model Chain" 
       width="300"/>
</p>

<h4 align="center">⚠️ Handle with care — work in progress</h4>

---
The **ATI** (Avalanche Terrain Identification) repository contains several modules and workflows to identify and
classify avalanche terrain.

## Modules

| Module         | Description                                                             | Documentation                                  |
|----------------|-------------------------------------------------------------------------|------------------------------------------------|
| `mod1Release`  | Tools to delineate and segment release areas                            | [documentation](documentation/mod1Release.md)  |
| `mod2Mobility` | Preparation and parameterization for avalanche mobility simulations     | [documentation](documentation/mod2Mobility.md) |
| `mod3Map`      | Postprocessing tools to interpret, map and represent simulation results | [documentation](documentation/mod3Map.md)      |

### Workflows

Suggestions for combining the individual modules into full processing chains:

- [autoATES Model Chain](documentation/workflowAutoAtesModelChain.md)
- [Avalanche Scenario Model Chain](documentation/workflowAvaScenarioModelChain.md)
- [Size Dependent Parameterization](documentation/workflowSizeDepParameterisation.md)
- [Thalweg Analysis Model Chain](documentation/workflowThalwegAnalysis.md)
- [Plots](documentation/plots.md)

---

## Installation (Linux)

### Requirements

Install [git](https://github.com/git-guides/install-git) and [pixi](https://pixi.sh/latest/#installation).

### Setup

Clone `AvalancheTerrainIdentification` and `AvaFrame` as sibling repositories:

```bash
  cd [YOURDIR]/OpenNHM
  git clone https://github.com/OpenNHM/AvalancheTerrainIdentification.git
  git clone https://github.com/OpenNHM/AvaFrame.git
  cd AvalancheTerrainIdentification
```

The workflows currently use the following AvaFrame branches:

| Workflow | AvaFrame branch |
|---|---|
| `runAutoAtesModelChain.py` | `PS_FP_changeCfgRead` |
| `runThalwegAnalysis.py` | `PS_FP_thalweg` |
| `runAvaScenModelChain.py` | `master` |

Use the branch required by the workflow you intend to run. The thalweg dependency and the use of `master` for the
AvaScenarioModelChain are confirmed. The AutoATES requirement is retained from the existing documentation until its
owner confirms otherwise.

### First Run

Follow these steps to run a workflow.

1. For this AutoATES example, select its documented AvaFrame branch and return to
   `AvalancheTerrainIdentification`:

```bash
  cd [YOURDIR]/OpenNHM/AvaFrame
  git switch PS_FP_changeCfgRead
  cd ../AvalancheTerrainIdentification
```

2. Activate the development environment:

```bash
  pixi shell --environment dev
```

3. Run a workflow, e.g. the autoATES model chain:

```bash
  python workflows/runAutoAtesModelChain.py
```

This performs a full autoATES workflow: PRA delineation and segmentation, avalanche mobility simulation with
`AvaFrame::com4FlowPy` using dynamic runout-angle and max-velocity parameterization, and classification with the
autoATES classifier. Results are saved to `data/avaTestBowl/Outputs/autoATES`.

The `workflows` folder contains further workflow examples.

### Initialize a project

Create a project folder where input data lie and where the results will be stored (check the module documentation linked
above for which input data is needed).

Copy the general configuration file `atiCfg.ini`:

```bash
cd modules
cp atiCfg.ini local_atiCfg.ini
```

and edit ``local_atiCfg.ini`` with your favorite text editor and set the `avalancheDirectory` variable to the full path
of your project folder.

Then provide the corresponding input data in `[avalancheDirectory]/Inputs`.

You can also have a look at the default setting for the module you want to use (e.g. ``runAutoAtesModelChainCfg.ini``
for the autoATES workflow). To use different settings, create a `local_` copy of the relevant `.ini` file and modify the
parameters as needed, analogous to the `local_atiCfg.ini` setup above.

#### Hint:

for the `runAutoAtesModelChain.py` and `runThalwegAnalysis.py` workflow, you need to
clone [AvaFrame](https://github.com/OpenNHM/AvaFrame)
in `[YOURDIR]`,
then activate the dev environment:

```bash
pixi shell --environment dev
```
The development environment uses the sibling AvaFrame checkout in editable mode. Changing that checkout's branch
therefore changes the AvaFrame implementation used by these workflows.
