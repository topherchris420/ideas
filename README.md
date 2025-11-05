# hello_os: Resonant Intelligence Playground 

> **A living research operating system exploring electromagnetic resonance, field dynamics, and physics**

Created by **Christopher Woodyard** | R.A.I.N. Lab | Vers3Dynamics 🇺🇸

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1rdR0r-m8CSoYTurllo6QXTw0MOueSmvZ)

---

## ⚡ Overview

**hello_os** (formerly `vers3dynamics`) is an experimental physics playground that combines:
- **Tesla coil resonant coupling simulations** with elliptic-integral precision
- **Numba-accelerated** computational physics (T4 GPU optimized)
- **Real-time visualizations** of electromagnetic field dynamics
- **Interactive parameter exploration** for wireless power transfer research

Built for researchers or anyone fascinated by resonance.

---

## 🔬 Current Experiments

### Tesla Resonant Coupling Simulator
The core module simulates magnetically-coupled resonant systems (Tesla coils) with:

**Physics Features:**
- **Mutual inductance calculation** using elliptic integrals (K and E)
- **Transient time-domain simulation** via coupled differential equations
- **Phasor steady-state analysis** for frequency response
- **Coupling coefficient (k)** computation from geometry
- **Phase-space dynamics** and energy transfer visualization

**Performance:**
- Numba JIT compilation for 100x+ speedup on efficiency maps
- Parallel computation of parameter sweeps
- GPU-accelerated contour generation

**Visualizations:**
- Time-domain current waveforms (Tx/Rx)
- Phase-space trajectories (steady-state)
- Energy dynamics (magnetic + capacitive)
- Frequency response curves (current & efficiency)
- **2D efficiency heatmaps** (distance vs frequency)
- **Living field animations** (breathing resonance patterns)

---

## 🚀 Quick Start

### Run on Google Colab (Easiest)
Click the Colab badge above to open the notebook and run immediately!

### Local Installation

```bash
# Clone the repository
git clone https://github.com/topherchris420/ideas.git
cd ideas

# Install dependencies
pip install numba matplotlib numpy scipy pandas ipywidgets tqdm

# Run the simulation (Jupyter required)
jupyter notebook vers3dynamics
