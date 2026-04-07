from __future__ import annotations

import argparse
from argparse import Namespace
from copy import deepcopy
from dataclasses import dataclass
import time
from typing import Any
from pathlib import Path

import matplotlib.pyplot as plt
from qm import QuantumMachinesManager
from qm import SimulationConfig
from qm.qua import align
from qm.qua import frame_rotation_2pi
from qm.qua import play
from qm.qua import program
from qm.qua import reset_frame
from qm.qua import reset_if_phase
from qm.qua import update_frequency
from qm.qua import wait
from qm_saas import QmSaas
from qm_saas import QOPVersion


LFM1_ELEMENT = "e1"
LFM2_ELEMENT = "e3"
CONTROLLER_NAME = "con1"
DEFAULT_CHANNEL = 2
QOP_VER = "v3_6_0"
HOST = "qm-saas.dev.quantum-machines.co"
QOP_IP = "172.16.33.115"
CLUSTER_NAME = "CS_3"
CHIRP_REPETITIONS = 2
CHIRP_START_HZ = int(20e6)
CHIRP_END_HZ = int(105e6)
CHIRP_DURATION_NS = int(256)
CHIRP_DURATION_CLOCKS = CHIRP_DURATION_NS // 4
GAP_DURATION_NS = int(64)
GAP_DURATION_CLOCKS = GAP_DURATION_NS // 4
CHIRP_RATE_HZ_PER_NS = (CHIRP_END_HZ - CHIRP_START_HZ) // CHIRP_DURATION_NS
PULSE_AMPLITUDE_VOLTS = 0.2
PHASE_SHIFT_TURNS = 0.25
LF_FEM_CHIRP_OUTPUT_SETTINGS = {
    "sampling_rate": 1e9,
    "upsampling_mode": "mw",
}


@dataclass(frozen=True)
class TestWave:
    """LF-FEM analog output settings for a single chirp element."""

    fem: int
    channel: int
    element_name: str

    def to_analog_output(self) -> dict[str, int]:
        """Build the analog output definition for this test wave."""

        return {"offset": 0}

    def to_element(self) -> dict[str, dict[str, object]]:
        """Build the QUA element definition for this test wave."""

        return {
            "singleInput": {
                "port": (CONTROLLER_NAME, self.fem, self.channel),
            },
            "operations": {
                "const": "constPulse",
            },
        }


def build_test_waves(selected_channel: int) -> list[TestWave]:
    """Create chirp wave definitions for the selected analog output channel."""

    return [
        TestWave(fem=3, element_name=LFM1_ELEMENT, channel=selected_channel),
        TestWave(fem=5, element_name=LFM2_ELEMENT, channel=selected_channel),
    ]


def build_elements(
    active_test_waves: list[TestWave],
) -> dict[str, dict[str, dict[str, object]]]:
    """Build QUA element definitions from the selected test waves."""

    return {
        test_wave.element_name: test_wave.to_element()
        for test_wave in active_test_waves
    }


def build_fems(active_test_waves: list[TestWave]) -> dict[int, dict[str, object]]:
    """Build OPX1000 FEM configuration for the selected test waves."""

    fem_ids = sorted({test_wave.fem for test_wave in active_test_waves})

    def build_analog_outputs(
        fem_test_waves: list[TestWave],
    ) -> dict[int, dict[str, int]]:
        return {
            test_wave.channel: test_wave.to_analog_output()
            for test_wave in fem_test_waves
        }

    return {
        fem_id: {
            "type": "LF",
            "analog_outputs": build_analog_outputs(
                [
                    test_wave
                    for test_wave in active_test_waves
                    if test_wave.fem == fem_id
                ]
            ),
            "digital_outputs": {
                1: {},
            },
            "analog_inputs": {
                1: {"offset": 0.0},
            },
        }
        for fem_id in fem_ids
    }


def build_base_config(selected_channel: int = DEFAULT_CHANNEL) -> dict[str, object]:
    """Build a full QUA configuration for the selected analog output channel."""

    active_test_waves = build_test_waves(selected_channel)
    return {
        "controllers": {
            CONTROLLER_NAME: {
                "type": "opx1000",
                "fems": build_fems(active_test_waves),
            },
        },
        "elements": build_elements(active_test_waves),
        "pulses": {
            "constPulse": {
                "operation": "control",
                "length": 1e5,
                "waveforms": {"single": "const_wf"},
            },
        },
        "waveforms": {
            "const_wf": {
                "type": "constant",
                "sample": 0.2,
            },
        },
        "digital_waveforms": {
            "ON": {"samples": [(1, 0)]},
        },
    }


def build_chirp_config(selected_channel: int) -> dict[str, object]:
    """Build the OPX configuration for the chirp program."""

    config = deepcopy(build_base_config(selected_channel=selected_channel))
    fems = config["controllers"][CONTROLLER_NAME]["fems"]
    for fem_config in fems.values():
        fem_config["analog_outputs"][selected_channel].update(
            LF_FEM_CHIRP_OUTPUT_SETTINGS
        )

    for element_name in (LFM1_ELEMENT, LFM2_ELEMENT):
        config["elements"][element_name]["intermediate_frequency"] = CHIRP_START_HZ

    config["pulses"]["constPulse"]["length"] = CHIRP_DURATION_NS
    config["waveforms"]["const_wf"]["sample"] = PULSE_AMPLITUDE_VOLTS
    return config


def build_program(config: dict[str, object]) -> Any:
    """Create the QUA program that plays the requested chirps."""

    element_names = [element_name for element_name in config["elements"]]
    if LFM1_ELEMENT not in element_names or LFM2_ELEMENT not in element_names:
        raise ValueError(
            "LFM1/LFM2 elements are not defined in the configuration.")

    with program() as qua_program:
        reset_if_phase(LFM2_ELEMENT)
        play(
            "const",
            LFM2_ELEMENT,
            # duration=CHIRP_DURATION_CLOCKS,
            chirp=(CHIRP_RATE_HZ_PER_NS, "Hz/nsec"),
        )

    return qua_program


def generate_serialized_program(qua_program, config: dict[str, object], filename="debug.py"):
    # generate serialized program
    from qm import generate_qua_script
    sourceFile = open(filename, 'w')
    print(generate_qua_script(qua_program, config), file=sourceFile) 
    sourceFile.close()


def online_simulation(config: dict[str, object]) -> None:
    """Run the chirp program on the QM online simulator."""

    from qm import SimulationConfig

    try:
        from user_profile import EMAIL
        from user_profile import PWD
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "atoms/user_profile.py.sample に倣って atoms/user_profile.py を作成してください。"
        ) from exc

    client = QmSaas(
        email=EMAIL,
        password=PWD,
        host=HOST,
    )

    with client.simulator(QOPVersion(QOP_VER)) as instance:
        qmm = QuantumMachinesManager(
            host=instance.host,
            port=instance.port,
            connection_headers=instance.default_connection_headers,
        )
        qua_program = build_program(config)
        generate_serialized_program(qua_program, config, "debug_online.py")
        simulation_duration = (
            CHIRP_REPETITIONS * (CHIRP_DURATION_CLOCKS +
                                 GAP_DURATION_CLOCKS) + 256
        )
        job = qmm.simulate(
            config,
            qua_program,
            SimulationConfig(simulation_duration),
        )
        samples = job.get_simulated_samples()
        samples.con1.plot()
        plt.show()


def run_on_hardware(config: dict[str, object]) -> None:
    """Run the chirp program on the real OPX1000 hardware."""

    qmm = QuantumMachinesManager(
        host=QOP_IP,
        cluster_name=CLUSTER_NAME,
    )
    qua_program = build_program(config)
    generate_serialized_program(qua_program, config, "debug_real.py")
    qm = qmm.open_qm(config, close_other_machines=True)
    qm.execute(qua_program)
    time.sleep(6)
    qm.close()


def run_simulation_on_hardware(config: dict[str, object]) -> None:
    """Run the chirp program on the real OPX1000 hardware."""

    qmm = QuantumMachinesManager(
        host=QOP_IP,
        cluster_name=CLUSTER_NAME,
    )
    qua_program = build_program(config)
    generate_serialized_program(qua_program, config, "debug_real_simulation.py")

    # Simulates the QUA program for the specified duration
    simulation_config = SimulationConfig(duration=500)  # In clock cycles = 4ns
    # Simulate blocks python until the simulation is done
    job = qmm.simulate(config, qua_program, simulation_config)
    # Get the simulated samples
    samples = job.get_simulated_samples()
    # Plot the simulated samples
    samples.con1.plot();plt.show()
    # Get the waveform report object
    waveform_report = job.get_simulated_waveform_report()
    # Cast the waveform report to a python dictionary
    waveform_dict = waveform_report.to_dict()
    # Visualize and save the waveform report
    waveform_report.create_plot(samples, plot=True, save_path=str(Path(__file__).resolve()))


def parse_args() -> Namespace:
    """Parse command line arguments."""

    parser = argparse.ArgumentParser(
        description="Play a repeated chirp on LFM1 and LFM2."
    )
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--real", dest="real_signals", action="store_true")
    mode_group.add_argument(
        "--online", dest="online_simulation", action="store_true")
    mode_group.add_argument("--real-simulation", dest="real_simulation", action="store_true")
    parser.add_argument(
        "--channel",
        type=int,
        default=DEFAULT_CHANNEL,
        help="LF-FEM analog output channel to use.",
    )
    return parser.parse_args()


def main() -> int:
    """Run the selected chirp execution mode."""

    args = parse_args()
    config = build_chirp_config(selected_channel=args.channel)

    if args.online_simulation:
        print("Run chirp with online simulation.")
        online_simulation(config)
        return 0

    if args.real_signals:
        print("Run chirp on OPX1000.")
        run_on_hardware(config)
        return 0

    if args.real_simulation:
        print("Run chirp with OPX1000 simulation.")
        run_simulation_on_hardware(config)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
 