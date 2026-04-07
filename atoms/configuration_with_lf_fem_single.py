"""
QUA-Config supporting OPX1000 w/ LF-FEM & External Mixers
"""

from pathlib import Path

import numpy as np
import plotly.io as pio
from qualang_tools.config.waveform_tools import drag_gaussian_pulse_waveforms
from qualang_tools.units import unit

pio.renderers.default = "browser"

#######################
# AUXILIARY FUNCTIONS #
#######################
u = unit(coerce_to_integer=True)


# IQ imbalance matrix
def IQ_imbalance(g, phi):
    """
    Creates the correction matrix for the mixer imbalance caused by the gain and phase imbalances, more information can
    be seen here:
    https://docs.qualang.io/libs/examples/mixer-calibration/#non-ideal-mixer
    :param g: relative gain imbalance between the 'I' & 'Q' ports. (unit-less), set to 0 for no gain imbalance.
    :param phi: relative phase imbalance between the 'I' & 'Q' ports (radians), set to 0 for no phase imbalance.
    """
    c = np.cos(phi)
    s = np.sin(phi)
    N = 1 / ((1 - g**2) * (2 * c**2 - 1))
    return [float(N * x) for x in [(1 - g) * c, (1 + g) * s, (1 - g) * s, (1 + g) * c]]


######################
# Network parameters #
######################
qop_ip = "127.0.0.1"  # Write the QM router IP address
cluster_name = None  # Write your cluster_name if version >= QOP220
qop_port = None  # Write the QOP port if version < QOP220


#####################
# OPX configuration #
#####################
con = "con1"
fem = 5
# Set octave_config to None if no octave are present
octave_config = None

sampling_rate = int(1e9)

#############################################
#                Resonators                 #
#############################################
# Continuous wave
const_len = 100
const_amp = 0.1

resonator_LO = 4.8 * u.GHz
resonator_IF = 60 * u.MHz

readout_len = 5000
readout_amp = 0.2

time_of_flight = 28
depletion_time = 2 * u.us


#############################################
#                  Config                   #
#############################################
config = {
    "version": 1,
    "controllers": {
        con: {
            "type": "opx1000",
            "fems": {
                fem: {
                    "type": "LF",
                    "analog_outputs": {
                        "7": {
                            "offset": 0.000000,
                            "output_mode": "direct",
                            "sampling_rate": 1000000000,
                            "upsampling_mode": "pulse",
                        },
                    },
                    "digital_outputs": {
                        "1": {},
                    },
                    "analog_inputs": {
                        "1": { 
                            "offset": 0.0,
                            "sampling_rate": 1000000000.0,
                            "gain_db": 0,
                        },
                    },
                },
                    
        },
    },
    },
    "elements": {
        "my_element": {
            "singleInput": {
                "port": (con, fem, 7),
            },
            "intermediate_frequency": 0.0, 
            "operations": {
                "readout": "readout_pulse",
            },
            "outputs": {
                "out1": (con, fem, 1),
            },
            "time_of_flight": time_of_flight,
            "smearing": 0,
        },
    },
    "pulses": {
        "readout_pulse": {
            "operation": "control",
            "length": 1728,
            "waveforms": {
                "single": "readout_wf",
            },
            "integration_weights": {
                "cos": "cosine_weights",
                "sin": "sine_weights",
                "minus_sin": "minus_sine_weights",
                "rotated_cos": "rotated_cosine_weights",
                "rotated_sin": "rotated_sine_weights",
                "rotated_minus_sin": "rotated_minus_sine_weights",
                "opt_cos": "opt_cosine_weights",
                "opt_sin": "opt_sine_weights",
                "opt_minus_sin": "opt_minus_sine_weights",
            },
            "digital_marker": "ON",
        },
        
    },
    "waveforms": {
        "readout_wf": {"type": "constant", "sample": 0.0}, 
    },
    "digital_waveforms": {
        "ON": {"samples": [(1, 0)]},
    },
    "integration_weights": {
        "cosine_weights": {
            "cosine": [(1.0, 5000)],
            "sine": [(0.0, 5000)],
        },
        "sine_weights": {
            "cosine": [(0.0, 5000)],
            "sine": [(1.0, 5000)],
        },
        "minus_sine_weights": {
            "cosine": [(0.0, 5000)],
            "sine": [(-1.0, 5000)],
        },
        "opt_cosine_weights": {
            "cosine": [(1.0, 5000)],
            "sine": [(0.0, 5000)],
        },
        "opt_sine_weights": {
            "cosine": [(0.0, 5000)],
            "sine": [(1.0, 5000)],
        },
        "opt_minus_sine_weights": {
            "cosine": [(0.0, 5000)],
            "sine": [(-1.0, 5000)],
        },
        "rotated_cosine_weights": {
            "cosine": [(1.0, 5000)],
            "sine": [(0.0, 5000)],
        },
        "rotated_sine_weights": {
            "cosine": [(-0.0, 5000)],
            "sine": [(1.0, 5000)],
        },
        "rotated_minus_sine_weights": {
            "cosine": [(0.0, 5000)],
            "sine": [(-1.0, 5000)],
        },
    },
}
