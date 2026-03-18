import os
from pathlib import Path
import numpy as np
from qualang_tools.config.waveform_tools import (
    drag_gaussian_pulse_waveforms,
    flattop_gaussian_waveform,
    drag_cosine_pulse_waveforms,
)
from qualang_tools.units import unit


######################
# Network parameters #
######################
# These should be changed to your credentials.
QOP_VER = "v3_6_0"
HOST = "qm-saas.quantum-machines.co"
EMAIL = "YOUR_EMAIL"
PWD = "YOUR_PASSWORD"


#######################
# AUXILIARY FUNCTIONS #
#######################
u = unit(coerce_to_integer=True)


#####################
# OPX configuration #
#####################
con = "con1"
lf_fem = 1
mw_fem = 2
# Set octave_config to None if no octave are present
octave_config = None


##################
# Util Functions #
##################


def blackman(t, v_start, v_end):
    """
    Amplitude waveform that minimizes the amount of side lobes in the Fourier domain.
    :param t: pulse duration [ns] (int)
    :param v_start: start amplitude [V] (float)
    :param v_end: end amplitude [V] (float)
    :return:
    """
    time_vector = np.asarray([x * 1.0 for x in range(int(t))])
    black = v_start + (
        time_vector / t
        - (25 / (42 * np.pi)) * np.sin(2 * np.pi * time_vector / t)
        + (1 / (21 * np.pi)) * np.sin(4 * np.pi * time_vector / t)
    ) * (v_end - v_start)
    return black


#############
# VARIABLES #
#############

# --> Array geometry
# Number of cols
num_cols = 8
# Number of rows
num_rows = 8
# Maximum number of tweezers available
max_num_tweezers = 8
# Number of configured tweezers, if it increases don't forget to update the "align" in the QUA program
n_tweezers = 8
n_segment_py = 50

# --> Chirp pulse
# Amplitude of each individual tweezer
# WARNING: total output cannot exceed 0.5V
const_pulse_amp = 0.5 / max_num_tweezers  # Must be < 0.49/max_num_tweezers
# Duration of tweezer frequency chirp
const_pulse_len = 100 * u.ns
# Analog readout threshold discriminating between atom and no-atom [V]
threshold = 0.0000

# --> Blackman pulses
# Amplitude of the Blackman pulse which should match the amplitude of the tweezers during frequency chirps
blackman_amp = const_pulse_amp
# Duration of the Blackman pulse for ramping up and down the tweezers power
blackman_pulse_len = 0.3 * u.ms
# Reduced sampling rate for generating long pulses without memory issues
sampling_rate = 100 * u.MHz  # Used for Blackman_long_pulse_len

# Tweezer col phases
phases_list = [0.1, 0.4, 0.9, 0.3, 0.7, 0.2, 0.5, 0.8, 0.0, 0.6]
# --> Col frequencies
col_spacing = -10 * u.MHz  # in Hz
col_IF_01 = 50 * u.MHz  # in Hz
col_IFs = [int(col_IF_01 + col_spacing * i) for i in range(num_cols)]
# --> Row frequencies
row_spacing = -10 * u.MHz  # in Hz
row_IF_01 = 50 * u.MHz  # in Hz
row_IFs = [row_IF_01 + row_spacing * x for x in range(num_rows)]

# Readout time of the occupation matrix sent by fpga
readout_fpga_len = 60
# Readout duration for acquiring the spectrographs
readout_pulse_len = blackman_pulse_len * 2 + const_pulse_len # 2 * u.us
short_readout_pulse_len = 0.4 * u.us

occupation_matrix_pulse_len = 3 * readout_fpga_len + 200
occupation_matrix_pulse_amp = 0.5

artiq_trigger_len = 20_000

# Voltage offset the col and row analog outputs
row_selector_voltage_offset = 0.0
col_selector_voltage_offset = 0.0

# Analog output connected to the col AOD
col_channel = 1
# Analog output connected to the row AOD
row_channel = 2


config = {
    "version": 1,
    "controllers": {
        con: {
            "type": "opx1000",
            "fems": {
                lf_fem: {
                    "type": "LF",
                    "analog_outputs": {
                        # 1: {
                        #     # Note, 'offset' takes absolute values, e.g., if in amplified mode and want to output 2.0 V, then set "offset": 2.0
                        #     "offset": max_frequency_point,
                        #     # The "output_mode" can be used to tailor the max voltage and frequency bandwidth, i.e.,
                        #     #   "direct":    1Vpp (-0.5V to 0.5V), 750MHz bandwidth (default)
                        #     #   "amplified": 5Vpp (-2.5V to 2.5V), 330MHz bandwidth
                        #     "output_mode": "amplified",
                        #     # The "sampling_rate" can be adjusted by using more FEM cores, i.e.,
                        #     #   1 GS/s: uses one core per output (default)
                        #     #   2 GS/s: uses two cores per output
                        #     # NOTE: duration parameterization of arb. waveforms, sticky elements and chirping
                        #     #       aren't yet supported in 2 GS/s.
                        #     "sampling_rate": sampling_rate,
                        #     # At 1 GS/s, use the "upsampling_mode" to optimize output for
                        #     #   modulated pulses (optimized for modulated pulses):      "mw"    (default)
                        #     #   unmodulated pulses (optimized for clean step response): "pulse"
                        #     "upsampling_mode": "pulse",
                        #     # Synchronization of the LF-FEM outputs with the MW-FEM outputs
                        #     # 141ns delay (band 1 and 3) or 161ns delay (band 2)
                        #     "delay": 141 * u.ns,
                        # },
                        col_channel: {"offset": col_selector_voltage_offset},  # Col AOD tone
                        row_channel: {"offset": row_selector_voltage_offset},  # Row AOD tone
                        7: {"offset": 0.0},  # Fake port for measurement
                        8: {"offset": 0.0},  # Fake port for measurement
                    },
                    "digital_outputs": {
                        1: {},
                    },
                    "analog_inputs": {
                        1: {"offset": 0.0},  # Analog input 1 used for fpga readout
                        # 2: {"offset": 0.0},  # Not used yet
                    },
                },
            },
        },
    },
    "elements": {
        # detector is used to acquire the spectrographs for debuging
        "detector": {
            "singleInput": {
                "port": (con, lf_fem, 8),
            },
            "intermediate_frequency": 0,
            "operations": {
                "const": "const_pulse",
                "readout": "readout_pulse",
                "short_readout": "short_readout_pulse",
            },
            "outputs": {
                "out1": (con, lf_fem, 1),
            },
            "time_of_flight": 24 + 176, # with ext. trigger: 24 + 176 ns
            "smearing": 0,
        },
        # row_selector is used to control the row AOD
        **{
            f"row_selector_{i + 1:02d}": {
                "singleInput": {
                    "port": (con, lf_fem, row_channel),
                },
                "intermediate_frequency": row_IFs[i],
                "operations": {
                    "blackman_up": "blackman_up_pulse",
                    "blackman_down": "blackman_down_pulse",
                    "const": "const_pulse",
                },
            }
            for i in range(n_tweezers)
        },
        # col_selector is used to control the column AOD
        **{
            f"col_selector_{i + 1:02d}": {
                "singleInput": {
                    "port": (con, lf_fem, col_channel),
                },
                "intermediate_frequency": col_IFs[i],
                "operations": {
                    "blackman_up": "blackman_up_pulse",
                    "blackman_down": "blackman_down_pulse",
                    "const": "const_pulse",
                },
            }
            for i in range(n_tweezers)
        },
        "trigger_artiq": {
            "digitalInputs": {
                "marker": {
                    "port": (con, lf_fem, 1),
                    "delay": 0,
                    "buffer": 0,
                },
            },
            "operations": {
                "on": "artiq_trigger_ON",
            },
        },
    },
    "pulses": {
        "readout_pulse": {
            "operation": "measurement",
            "length": readout_pulse_len,
            "waveforms": {
                "single": "zero_wf",
            },
            "integration_weights": {
                "cos": "cosine_weights",
                "sin": "sine_weights",
                "const": "const_weights",
            },
            "digital_marker": "ON",
        },
        "short_readout_pulse": {
            "operation": "measurement",
            "length": short_readout_pulse_len,
            "waveforms": {
                "single": "zero_wf",
            },
            "integration_weights": {
                "cos": "cosine_weights",
                "sin": "sine_weights",
            },
            "digital_marker": "ON",
        },
        "blackman_up_pulse": {
            "operation": "control",
            "length": blackman_pulse_len,
            "waveforms": {
                "single": "blackman_up_wf",
            },
            "digital_marker": "ON",
        },
        "blackman_down_pulse": {
            "operation": "control",
            "length": blackman_pulse_len,
            "waveforms": {
                "single": "blackman_down_wf",
            },
            "digital_marker": "ON",
        },
        "const_pulse": {
            "operation": "control",
            "length": const_pulse_len,
            "waveforms": {
                "single": "const_wf",
            },
            "digital_marker": "ON",
        },
        "unit_pulse": {
            "operation": "control",
            "length": occupation_matrix_pulse_len,
            "waveforms": {
                "single": "unit_wf",
            },
            "digital_marker": "ON",
        },
        "zero_pulse": {
            "operation": "control",
            "length": occupation_matrix_pulse_len,
            "waveforms": {
                "single": "zero_wf",
            },
            "digital_marker": "ON",
        },
        "artiq_trigger_ON": {
            "operation": "control",
            "length": artiq_trigger_len,
            "digital_marker": "ON",
        },
    },
    "waveforms": {
        "blackman_up_wf": {
            "type": "arbitrary",
            "samples": blackman(blackman_pulse_len / (1e9 / sampling_rate), 0, blackman_amp),
            "sampling_rate": sampling_rate,
        },
        "blackman_down_wf": {
            "type": "arbitrary",
            "samples": blackman(blackman_pulse_len / (1e9 / sampling_rate), blackman_amp, 0),
            "sampling_rate": sampling_rate,
        },
        "const_wf": {
            "type": "constant",
            "sample": const_pulse_amp,
        },
        "unit_wf": {
            "type": "constant",
            "sample": occupation_matrix_pulse_amp,
        },
        "zero_wf": {
            "type": "constant",
            "sample": 0.0,
        },
    },
    "digital_waveforms": {
        "ON": {"samples": [(1, 0)]},
    },
    "integration_weights": {
        "const_fpga_weights": {
            "cosine": [(1.0, readout_fpga_len)],
            "sine": [(0.0, readout_fpga_len)],
        },
        "const_weights": {
            "cosine": [(1.0, readout_pulse_len)],
            "sine": [(0.0, readout_pulse_len)],
        },
        "cosine_weights": {
            "cosine": [(1.0, readout_pulse_len)],
            "sine": [(0.0, readout_pulse_len)],
        },
        "sine_weights": {
            "cosine": [(0.0, readout_pulse_len)],
            "sine": [(1.0, readout_pulse_len)],
        },
    },
}