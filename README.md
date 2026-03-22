# EzGolf 🏌️‍♂️

Just download and run the .exe to get going on Windows. 

**EzGolf** is a Python-based golf swing analyzer designed to help golfers break down their mechanics. By leveraging high-performance video playback, it provides a smooth interface for reviewing swing frames and identifying areas for improvement.

## 🌟 Features
* **High-Fidelity Playback:** Uses the `libmpv` engine for frame-accurate seeking.
* **Swing Analysis:** Tools to review posture, club path, and impact positions.
* **Portable:** Can be compiled into a single `.exe` for use on any Windows machine without requiring a Python installation.

## 🛠 Tech Stack
* **Language:** Python 3.x
* **Video Engine:** [mpv](https://mpv.io/) (via `mpv-1.dll`)
* **Graphics Support:** Direct3D Compiler (`d3dcompiler_43.dll`)
* **UI/Assets:** Cool nostalgic icon maybe you know it too (`ezgolf.jpg`)

## 🚀 Getting Started

### Prerequisites
To run the source code, you will need:
* Python 3.10+
* The following DLLs in the root directory (included in the release bundle):
    * `mpv-1.dll`
    * `d3dcompiler_43.dll`

### Installation
1. Clone the repository:
   ```bash
   git clone [https://github.com/camwin/EzGolf.git](https://github.com/camwin/EzGolf.git)
   cd EzGolf
   python ezGolf.py

### 📸 Screenshots

<p align="center">
  <img src="567302736-6d1cbc3d-4986-4667-a0f3-216af8598442.png" alt="Main Interface" />

  <img src="567302767-f00454e4-baf1-4215-b4e5-4d9b3d0bbe62.png" alt="Swing Path Drawing" />

  <img src="567303133-2ed9fb60-ae68-4a61-baab-6b57b0fb5599.png" alt="Side-by-Side Analysis" />

  <img src="posture_1.png" alt="Posture Analysis" />

  <img src="homa.png" alt="Posture Analysis" />

</p>
