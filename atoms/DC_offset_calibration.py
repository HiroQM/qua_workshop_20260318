#%%
"""
LF-FEM DC offset auto-calibration

This script performs two separate calibrations for a given element:

1) Input DC offset calibration
   - Uses the element's readout path (ELEM_NAME + output port).
   - Adjusts analog_inputs[...] ["offset"] on the LF-FEM.
   - Should be run with NOTHING connected to the analog input (open input).

2) Output DC offset calibration
   - Uses the same readout element and a loopback from AO -> AI.
   - Adjusts analog_outputs[...] ["offset"].
   - Requires a physical loopback cable.

Both calibrations:
- Use slope estimation + bounded correction (anti-overshoot).
- Update ONLY the relevant FEM/port 'offset' back into
  configuration_with_lf_fem_single.py (with a .bak backup).

If you use analog_inputs[2], change atr_r1.input1() -> atr_r1.input2()
in the stream_processing section.
"""

# =========================
# Imports
# =========================
from qm.qua import *
from qm import QuantumMachinesManager
from configuration_with_lf_fem_single import *  # config, con, fem, qop_ip, qop_port, cluster_name, etc.
from qualang_tools.units import unit
import numpy as np
from pathlib import Path
from copy import deepcopy
from datetime import datetime
import re
from typing import Optional, Tuple

# =========================
# Parameters (edit as needed)
# =========================
u = unit(coerce_to_integer=True)
n_avg = 100

ELEM_NAME = "my_element"
OUTPUT_KEY = "out1"      # key in elements[ELEM_NAME]["outputs"]

tol_mV = 0.5
max_iters = 6
max_abs_offset_V = 1.0
MAX_STEP_V = 0.1         # per-iteration max |Δoffset| [V]
UPDATE_ON_FAIL = False   # if not converged, still update config file?

# =========================
# Helpers: paths & clamps
# =========================
def _clamp(x, lo, hi):
    return max(lo, min(hi, x))

def resolve_config_path(filename: str) -> Path:
    """Robust path resolution for script/REPL/Notebook."""
    try:
        base = Path(__file__).parent
    except NameError:
        base = Path.cwd()
    p = (base / filename).resolve()
    if not p.exists():
        raise FileNotFoundError(
            f"[Path] Config file not found: '{p}'. "
            f"Resolved from base='{base}'. Verify the file name/location."
        )
    return p

def create_backup(cfg_path: Path) -> Path:
    """Create a timestamped .bak alongside the config before modifying it."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = cfg_path.with_suffix(cfg_path.suffix + f".{ts}.bak")
    bak.write_text(cfg_path.read_text(encoding="utf-8"), encoding="utf-8")
    return bak

# =========================
# Helpers: in-memory config offsets
# =========================
def get_ai_offset(cfg: dict, elem_name: str, output_key: str) -> float:
    """Get current analog input offset from controller/FEM referenced by element's output."""
    con_, fem_, port_ = cfg["elements"][elem_name]["outputs"][output_key]
    return float(cfg["controllers"][con_]["fems"][fem_]["analog_inputs"][str(port_)]["offset"])

def set_ai_offset(cfg: dict, elem_name: str, output_key: str, new_offset_v: float, max_abs: float):
    """Set analog input offset (clamped) via element's output mapping."""
    con_, fem_, port_ = cfg["elements"][elem_name]["outputs"][output_key]
    ai = cfg["controllers"][con_]["fems"][fem_]["analog_inputs"][str(port_)]
    ai["offset"] = _clamp(float(new_offset_v), -max_abs, max_abs)

def get_ao_offset(cfg: dict, elem_name: str) -> float:
    """Get current analog output offset from the element's singleInput port."""
    con_, fem_, port_ = cfg["elements"][elem_name]["singleInput"]["port"]
    return float(cfg["controllers"][con_]["fems"][fem_]["analog_outputs"][str(port_)]["offset"])

def set_ao_offset(cfg: dict, elem_name: str, new_offset_v: float, max_abs: float):
    """Set analog output offset (clamped) via element's singleInput port."""
    con_, fem_, port_ = cfg["elements"][elem_name]["singleInput"]["port"]
    ao = cfg["controllers"][con_]["fems"][fem_]["analog_outputs"][str(port_)]
    ao["offset"] = _clamp(float(new_offset_v), -max_abs, max_abs)

# =========================
# Helpers: text patching in config file
# =========================
def _update_offset_in_block(
    config_py_path: Path,
    block_key: str,       # "analog_inputs" or "analog_outputs"
    target_port: int,
    new_offset_v: float,
):
    """
    Generic text-based update of '<block_key>["target_port"]["offset"]' in config file.

    Looks for a pattern like:

        "analog_inputs": {
            "1": {
                "offset": <number>,
                ...
            },
            ...
        }

    and replaces <number> with new_offset_v.
    """
    text = config_py_path.read_text(encoding="utf-8")

    pat = re.compile(
        r'("' + re.escape(block_key) + r'"\s*:\s*{[\s\S]*?"'
        + re.escape(str(int(target_port)))
        + r'"\s*:\s*{[\s\S]*?"offset"\s*:\s*)'
        r'(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)',
        flags=re.S,
    )

    new_text, n = pat.subn(lambda m: f"{m.group(1)}{float(new_offset_v):.6f}", text, count=1)
    if n != 1:
        raise RuntimeError(
            f"[Update] Failed to update 'offset' for {block_key}[{target_port}] "
            f"in '{config_py_path.resolve()}'. Matches found: {n}. "
            f"Check that the block and port exist and are written as expected."
        )

    config_py_path.write_text(new_text, encoding="utf-8")

def update_input_offset_to_config_py(
    config_py_path: Path,
    iter_cfg: dict,
    elem_name: str,
    output_key: str,
    new_offset_v: float,
):
    """Validate against runtime config, then patch analog_inputs in the config file."""
    con_, fem_rt, port_rt = iter_cfg["elements"][elem_name]["outputs"][output_key]

    fem_block = iter_cfg["controllers"][con_]["fems"].get(fem_rt)
    if fem_block is None:
        raise RuntimeError(f"[Update] FEM {fem_rt} not found under controller '{con_}' in runtime config.")
    if fem_block.get("type") != "LF":
        raise RuntimeError(
            f"[Update] FEM {fem_rt} under controller '{con_}' is not LF "
            f"(type={fem_block.get('type')})."
        )
    if "analog_inputs" not in fem_block:
        raise RuntimeError(
            f"[Update] FEM {fem_rt} under controller '{con_}' has no 'analog_inputs' block."
        )
    if str(port_rt) not in fem_block["analog_inputs"]:
        raise RuntimeError(
            f"[Update] Target AI port {port_rt} not present under FEM {fem_rt} in runtime config."
        )

    _update_offset_in_block(config_py_path, "analog_inputs", target_port=port_rt, new_offset_v=new_offset_v)

def update_output_offset_to_config_py(
    config_py_path: Path,
    iter_cfg: dict,
    elem_name: str,
    new_offset_v: float,
):
    """Validate against runtime config, then patch analog_outputs in the config file."""
    con_, fem_rt, port_rt = iter_cfg["elements"][elem_name]["singleInput"]["port"]

    fem_block = iter_cfg["controllers"][con_]["fems"].get(fem_rt)
    if fem_block is None:
        raise RuntimeError(f"[Update] FEM {fem_rt} not found under controller '{con_}' in runtime config.")
    if fem_block.get("type") != "LF":
        raise RuntimeError(
            f"[Update] FEM {fem_rt} under controller '{con_}' is not LF "
            f"(type={fem_block.get('type')})."
        )
    if "analog_outputs" not in fem_block:
        raise RuntimeError(
            f"[Update] FEM {fem_rt} under controller '{con_}' has no 'analog_outputs' block."
        )
    if str(port_rt) not in fem_block["analog_outputs"]:
        raise RuntimeError(
            f"[Update] Target AO port {port_rt} not present under FEM {fem_rt} in runtime config."
        )

    _update_offset_in_block(config_py_path, "analog_outputs", target_port=port_rt, new_offset_v=new_offset_v)

# =========================
# Measurement helper
# =========================
def get_measured_dc_volts(qmm: QuantumMachinesManager, cfg: dict, prg):
    """Run the QUA program once; return (DC volts real avg, averaged ADC trace)."""
    qm = qmm.open_qm(cfg)
    try:
        job = qm.execute(prg)
        res = job.result_handles
        res.wait_for_all_values()
        adc_avg = u.raw2volts(res.get("adc1").fetch_all())
        dc_v = float(np.mean(adc_avg.real))
        return dc_v, adc_avg
    finally:
        qm.close()

# =========================
# QUA program
# =========================
with program() as prog:
    v1 = declare(int)
    atr_r1 = declare_stream(adc_trace=True)
    with for_(v1, 0, v1 < n_avg, v1 + 1):
        reset_if_phase(ELEM_NAME)
        measure("readout", ELEM_NAME, adc_stream=atr_r1)
        # wait(5000, ELEM_NAME)  # enable if your analog chain needs more settling
    with stream_processing():
        # If you use analog_inputs[2], change input1() -> input2()
        atr_r1.input1().average().save("adc1")
        atr_r1.input1().save("adc1_single_run")

# =========================
# Generic calibration routine
# =========================
def run_offset_calibration(
    label: str,
    qmm: QuantumMachinesManager,
    iter_cfg: dict,
    elem_name: str,
    get_offset_fn,
    set_offset_fn,
    initial_offset_v: float,
):
    """Common loop for offset calibration (used for both input and output)."""
    print(f"\n=== {label}: Pre-calibration (slope) ===")
    step_V = 0.05

    # Pre-calibration slope estimation
    set_offset_fn(iter_cfg, elem_name, initial_offset_v - step_V, max_abs_offset_V)
    dc_v1, _ = get_measured_dc_volts(qmm, iter_cfg, prog)
    print(f"[Calib] offset {initial_offset_v - step_V:+.6f} V -> {dc_v1 * 1e3:+.3f} mV")

    set_offset_fn(iter_cfg, elem_name, initial_offset_v + step_V, max_abs_offset_V)
    dc_v2, _ = get_measured_dc_volts(qmm, iter_cfg, prog)
    print(f"[Calib] offset {initial_offset_v + step_V:+.6f} V -> {dc_v2 * 1e3:+.3f} mV")

    slope_V_per_V = (dc_v2 - dc_v1) / (2 * step_V)
    if abs(slope_V_per_V) < 1e-6:
        print("[Calib] Warning: measured slope too small, defaulting to 1.0")
        slope_V_per_V = 1.0

    apply_scale = abs(slope_V_per_V)
    sign_coupling = np.sign(slope_V_per_V)
    print(
        f"[Calib] slope = {slope_V_per_V:+.3f} (V_DC/V_offset), apply_scale = {apply_scale:.3f}, "
        f"coupling = {'neg (offset↑→DC↓)' if sign_coupling < 0 else 'pos (offset↑→DC↑)'}"
    )

    # Restore baseline
    set_offset_fn(iter_cfg, elem_name, initial_offset_v, max_abs_offset_V)

    print(f"\n=== {label}: Iterative cancellation ===")
    offset_history_V, dc_history_mV = [], []
    converged = False
    iters_run = 0
    last_adc = None

    for k in range(1, max_iters + 1):
        iters_run = k
        current_offset_v = get_offset_fn(iter_cfg, elem_name)
        dc_v, adc_avg = get_measured_dc_volts(qmm, iter_cfg, prog)
        last_adc = adc_avg

        dc_mV = dc_v * 1e3
        offset_history_V.append(current_offset_v)
        dc_history_mV.append(dc_mV)

        print(f"[Iter {k}] offset = {current_offset_v:+.6f} V, DC = {dc_mV:+.3f} mV")

        if abs(dc_mV) <= tol_mV:
            print(f"[Done] |DC| ≤ {tol_mV} mV at {current_offset_v:+.6f} V")
            converged = True
            break

        raw = (dc_v / apply_scale)
        correction = (+raw) if (sign_coupling < 0) else (-raw)
        correction = np.sign(correction) * min(abs(correction), MAX_STEP_V)  # anti-overshoot
        new_offset_v = current_offset_v + correction

        set_offset_fn(iter_cfg, elem_name, new_offset_v, max_abs_offset_V)
        print(f"[Iter {k}] apply Δ = {correction:+.6f} V → new offset {new_offset_v:+.6f} V")

    return {
        "converged": converged,
        "iters_run": iters_run,
        "apply_scale": apply_scale,
        "sign_coupling": sign_coupling,
        "offset_history_V": offset_history_V,
        "dc_history_mV": dc_history_mV,
        "last_adc": last_adc,
    }

#%%
# =========================
# 1) INPUT CALIBRATION (no cable connected to input)
# =========================

# Connect & prepare config
qmm = QuantumMachinesManager(host=qop_ip, port=qop_port, cluster_name=cluster_name)
iter_cfg = deepcopy(config)

con_out, in_fem_, in_port_ = iter_cfg["elements"][ELEM_NAME]["outputs"][OUTPUT_KEY]
con_in, out_fem_, out_port_ = iter_cfg["elements"][ELEM_NAME]["singleInput"]["port"]
assert con_out == con_in
con_ = con_out  # single controller

ao0 = get_ao_offset(iter_cfg, ELEM_NAME)
ai0 = get_ai_offset(iter_cfg, ELEM_NAME, OUTPUT_KEY)

print(f"[Info] AO start offset = {ao0:+.6f} V (con='{con_}', fem={out_fem_}, port={out_port_})")
print(f"[Info] AI start offset = {ai0:+.6f} V (con='{con_}', fem={in_fem_},  port={in_port_})")

# Run input calibration
inp_result = run_offset_calibration(
    label="INPUT OFFSET CALIBRATION",
    qmm=qmm,
    iter_cfg=iter_cfg,
    elem_name=ELEM_NAME,
    get_offset_fn=lambda cfg, elem: get_ai_offset(cfg, elem, OUTPUT_KEY),
    set_offset_fn=lambda cfg, elem, v, max_abs: set_ai_offset(cfg, elem, OUTPUT_KEY, v, max_abs),
    initial_offset_v=ai0,
)
final_ai_offset = get_ai_offset(iter_cfg, ELEM_NAME, OUTPUT_KEY)

# Summary
ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
print("\n" + "=" * 60)
print(" INPUT DC OFFSET CALIBRATION SUMMARY")
print("=" * 60)
print(f" Timestamp       : {ts}")
print(f" Controller      : {con_}")
print(f" FEM             : {in_fem_}")
print(f" Element         : {ELEM_NAME}")
print(f" AI Port         : {in_port_}")
print("-" * 60)
print(f" Start offset [V]: {ai0:.6f}")
print(f" Final offset [V]: {final_ai_offset:.6f}")
print(f" Converged       : {inp_result['converged']}")
print(f" Iterations      : {inp_result['iters_run']}")
print("=" * 60 + "\n")

# Update config file for input
cfg_path = resolve_config_path("configuration_with_lf_fem_single.py")
if inp_result["converged"] or UPDATE_ON_FAIL:
    bak_path = create_backup(cfg_path)
    try:
        update_input_offset_to_config_py(
            cfg_path, iter_cfg, ELEM_NAME, OUTPUT_KEY, new_offset_v=final_ai_offset
        )
    except Exception as e:
        raise RuntimeError(
            f"[Update] Error while updating INPUT offset in '{cfg_path.resolve()}' "
            f"(con='{con_}', fem={in_fem_}, port={in_port_}). Backup kept at '{bak_path}'. "
            f"Details: {e}"
        ) from e

    # reflect in-memory original config as well
    config["controllers"][con_]["fems"][in_fem_]["analog_inputs"][str(in_port_)]["offset"] = final_ai_offset
    print(
        f"[Update] Updated INPUT offset in '{cfg_path.name}' "
        f"(con='{con_}', fem={in_fem_}, port={in_port_}). Backup: '{bak_path.name}'"
    )
else:
    print(
        f"[Update] Skipped writing INPUT offset to '{cfg_path.name}' "
        f"because calibration did not converge (UPDATE_ON_FAIL={UPDATE_ON_FAIL})."
    )

#%%
# =========================
# 2) PAUSE TO CHANGE CABLING
# =========================

print("\n*** Now connect the loopback from AO (port "
      f"{out_port_}) to AI (port {in_port_}) ***")

#%%
# =========================
# 3) OUTPUT CALIBRATION (with loopback)
# =========================

out_result = run_offset_calibration(
    label="OUTPUT OFFSET CALIBRATION",
    qmm=qmm,
    iter_cfg=iter_cfg,
    elem_name=ELEM_NAME,
    get_offset_fn=get_ao_offset,
    set_offset_fn=set_ao_offset,
    initial_offset_v=ao0,
)
final_ao_offset = get_ao_offset(iter_cfg, ELEM_NAME)

# Summary
ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
print("\n" + "=" * 60)
print(" OUTPUT DC OFFSET CALIBRATION SUMMARY")
print("=" * 60)
print(f" Timestamp       : {ts}")
print(f" Controller      : {con_}")
print(f" FEM             : {out_fem_}")
print(f" Element         : {ELEM_NAME}")
print(f" AO Port         : {out_port_}")
print("-" * 60)
print(f" Start offset [V]: {ao0:.6f}")
print(f" Final offset [V]: {final_ao_offset:.6f}")
print(f" Converged       : {out_result['converged']}")
print(f" Iterations      : {out_result['iters_run']}")
print("=" * 60 + "\n")

# Update config file for output
cfg_path = resolve_config_path("configuration_with_lf_fem_single.py")
if out_result["converged"] or UPDATE_ON_FAIL:
    bak_path = create_backup(cfg_path)
    try:
        update_output_offset_to_config_py(
            cfg_path, iter_cfg, ELEM_NAME, new_offset_v=final_ao_offset
        )
    except Exception as e:
        raise RuntimeError(
            f"[Update] Error while updating OUTPUT offset in '{cfg_path.resolve()}' "
            f"(con='{con_}', fem={out_fem_}, port={out_port_}). Backup kept at '{bak_path}'. "
            f"Details: {e}"
        ) from e

    # reflect in-memory original config as well
    config["controllers"][con_]["fems"][out_fem_]["analog_outputs"][str(out_port_)]["offset"] = final_ao_offset
    print(
        f"[Update] Updated OUTPUT offset in '{cfg_path.name}' "
        f"(con='{con_}', fem={out_fem_}, port={out_port_}). Backup: '{bak_path.name}'"
    )
else:
    print(
        f"[Update] Skipped writing OUTPUT offset to '{cfg_path.name}' "
        f"because calibration did not converge (UPDATE_ON_FAIL={UPDATE_ON_FAIL})."
    )
