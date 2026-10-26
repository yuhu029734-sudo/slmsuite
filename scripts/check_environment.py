"""Check the interpreter, scientific stack, and a simulated holography workflow."""

import argparse
import importlib.metadata
import importlib.util
import json
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-gpu", action="store_true")
    args = parser.parse_args()
    os.environ.setdefault("MPLBACKEND", "Agg")

    import cv2
    import h5py
    import ipykernel
    import ipywidgets
    import numpy as np
    import scipy

    import slmsuite
    from slmsuite.hardware.slms.simulated import SimulatedSLM
    from slmsuite.holography.algorithms import Hologram

    project_root = Path(__file__).resolve().parents[1]
    expected_prefix = project_root / ".venv"
    if Path(sys.prefix).resolve() != expected_prefix.resolve():
        raise RuntimeError(
            f"Use this project's interpreter: {expected_prefix / 'Scripts/python.exe'}"
        )
    if not Path(slmsuite.__file__).resolve().is_relative_to(project_root / "slmsuite"):
        raise RuntimeError("slmsuite is not imported from this checkout")

    report = {
        "python": sys.version.split()[0],
        "interpreter": sys.executable,
        "slmsuite": slmsuite.__version__,
        "source": slmsuite.__file__,
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "opencv": cv2.__version__,
        "h5py": h5py.__version__,
        "ipykernel": ipykernel.__version__,
        "ipywidgets": ipywidgets.__version__,
        "pytest": importlib.metadata.version("pytest"),
    }
    if importlib.util.find_spec("cupy") is not None:
        import cupy as cp

        props = cp.cuda.runtime.getDeviceProperties(0)
        cp.random.seed(7)
        values = cp.arange(10, dtype=cp.float32)
        if float(cp.sum(values).get()) != 45.0:
            raise RuntimeError("CUDA array calculation failed")
        cp.fft.fft(values).get()
        report["gpu"] = props["name"].decode()
        report["cupy"] = cp.__version__
        report["cuda_runtime"] = cp.cuda.runtime.runtimeGetVersion()
    elif args.require_gpu:
        raise RuntimeError("GPU dependencies are missing; run scripts/setup.ps1 -Gpu")
    else:
        report["gpu"] = "CPU mode (optional CuPy is not installed)"

    target = np.zeros((64, 64), dtype=np.float32)
    target[28, 28] = target[28, 36] = target[36, 28] = target[36, 36] = 1
    hologram = Hologram(target)
    hologram.optimize("GS", maxiter=10, verbose=False)
    phase = hologram.get_phase()
    if phase.shape != target.shape or not np.isfinite(phase).all() or hologram.iter != 10:
        raise RuntimeError("Gerchberg-Saxton hologram optimization failed")
    slm = SimulatedSLM(resolution=(64, 64), wav_um=0.78, pitch_um=(8, 8), gpu=False)
    try:
        slm.set_phase(phase)
        if slm.display.shape != target.shape:
            raise RuntimeError("Simulated SLM phase display failed")
    finally:
        slm.close()
    report["hologram_backend"] = type(hologram.phase).__module__
    report["simulation"] = "64 x 64, four target spots, 10 GS iterations, simulated SLM: OK"
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
