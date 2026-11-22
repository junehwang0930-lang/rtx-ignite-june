# Portable Counter-UAS Deployment Kit (Kyle Field example)

Team 20 entry for the **2026 RTX Ignite Design Challenge**: a portable counter-UAS deployment kit for large outdoor civilian events. Kyle Field (Texas A&M) is our worked example; other venues use the same kits after a site survey.

**Scope:** detection, tracking, assessment, recommendations and human review, plus a non-kinetic effector module (directional RF control-link jammer) in the kit. Only a certified law-enforcement officer may operate the effector, under the SAFER SKIES Act (6 U.S.C. 124n) requirements. The software only recommends and never transmits on its own. The kit contains no kinetic or takeover hardware; net-capture interceptors are covered as design analysis only.

![System architecture](Figures/system_architecture.png)

## Design at a glance

| Site | Count | Sensors |
|---|---|---|
| Garage kit: top decks of Central Campus Garage and West Campus Garage | 2 | 360° radar, long-range EO/IR camera, RF sensor |
| Edge kit: Kyle Field corner pavilion roofs | 4 | EO/IR camera, RF sensor |
| Effector kit (proposed): fixed directional RF jammer at each garage + one portable unit | 3 | Certified officer only |
| **Total** | **6 sites** | **2 radars, 6 cameras, 6 RF sensors** |

## Repository layout

| Folder | Contents |
|---|---|
| [`ML Files/`](ML%20Files) | **Current:** [`real_ml/`](ML%20Files/real_ml) — real NRC radar data pipeline (713 validated labeled tracks, features, quality reports) for object classification. Offline BIRD/UAV baselines evaluated on held-out recording days. **Earlier prototype:** simulator, simulated data and model kept for reference. Radar site survey code is in `site_survey/`. |
| [`CAD Files/`](CAD%20Files) | FreeCAD models (`.FCStd`) of both kits, the deployment cases, the command post kit, and Kyle Field with the kits installed, plus rendered images in `Renders/`. |
| [`Coverage Maps/`](Coverage%20Maps) | Interactive coverage viewer (download `Kyle_Field_v9_Coverage_Viewer.html` and open it in a browser), RF / camera envelope map (PNG and SVG), and the radar line-of-sight site survey image. See `README_Revised.txt` for the viewer's assumptions; the survey code is in `ML Files/site_survey/`. |
| [`3D Simulation Files/`](3D%20Simulation%20Files) | Interactive demo of the earlier simulated prototype (layout, operator view, sensor toggles). Download `cuas_demo.html` and open it in Chrome. Its on-screen calls come from the older simulated model, not the current classifier. |
| [`Figures/`](Figures) | System architecture, geofenced response decision flow (with the RF effector and escalation ladder) and the data-flow components figure (PNG/PDF/SVG). |

## Running the ML pipeline

For the independent **real-world radar data pipeline**, see
[`ML Files/real_ml/README.md`](ML%20Files/real_ml/README.md). It validates NRC measurements and compares offline BIRD/UAV classifiers. The selected tree reached 82.7% balanced accuracy on 82 later-day tracks. [Results and limitations](ML%20Files/real_ml/reports/presentation_summary.md) The simulation commands below are preserved for reference.

```bash
cd "ML Files"
pip install -r requirements.txt
python rules_baseline.py      # rules-only alarm vs. model alarm on the test snapshots
python latency_study.py       # fusion + model timing
```

See `ML Files/README.md` for the full pipeline (case generation, simulation, training, studies and demo build), what the simulator does and does not model, and how the reported numbers were produced.

## Important caveats

- **Real-data evaluation covers completed bird and UAV tracks only.** Older numbers in the simulated prototype are not real-world results.
- The NRC data comes from one radar family in Quebec and is mostly birds (146 UAV tracks), so it may not transfer directly to a Texas stadium.
- The effector kit is a concept: no specific authorized product selected, not in CAD, not tested.
- Coverage figures are geometric line of sight using estimated building heights, with no terrain or trees.
- Traffic mix, drone sizes, power estimates, setup times and alert-zone sizes are design assumptions.

## AI use

We designed the system: sensor choice and placement, fusion concept, rules for identifying legitimate drones and swarms, human review and geofenced response logic. AI tools helped implement parts from our specifications: the 3D simulation and demo website (earlier prototype), the data pipeline code, the system architecture and response-flow diagrams, and the CAD models. AI also helped run calculations from methods and sources we specified and helped edit our writeup. See Section 17 of our writeup for details.
