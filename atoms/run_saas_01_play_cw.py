# %%
import matplotlib.pyplot as plt
from configuration_opx1000_mwfem_lffem import *
from qm import LoopbackInterface, QuantumMachinesManager, SimulationConfig
from qm.qua import *
from qm_saas import QmSaas, QOPVersion

# Initialize QOP simulator client
client = QmSaas(email=EMAIL, password=PWD, host=HOST)

with client.simulator(QOPVersion(QOP_VER)) as instance:
    # Initialize QuantumMachinesManager with the simulation instance details
    qmm = QuantumMachinesManager(
        host=instance.host,
        port=instance.port,
        connection_headers=instance.default_connection_headers,
    )

    ###################
    # The QUA program #
    ###################

    with program() as PROG:
        
        # # case1
        # play("const", "col_selector_01") # 100MHz, 1us

        # # case2
        # play("const", "col_selector_01", chirp=(100, "GHz/sec")) # 100MHz -> 120MHz

        # # case3
        # update_frequency("col_selector_01", 80 * u.MHz)
        # play("const", "col_selector_01") # 80MHz, 1us

        # # case4
        # update_frequency("col_selector_01", 80 * u.MHz)
        # play("const", "col_selector_01", chirp=(100, "GHz/sec")) # 80MHz -> 100MHz

        # # case5
        # # f01 = 75MHz # QUA variable on FPGA
        # update_frequency("col_selector_01", f01)
        # play("const", "col_selector_01", chirp=(100, "GHz/sec")) # f01 MHz -> (f01 + 20)MHz

        # # case6
        # # f01 = 75MHz # QUA variable on FPGA
        # # t01 = 500 ns # QUA variable on FPGA
        # update_frequency("col_selector_01", f01)
        # play("const", "col_selector_01", chirp=(100, "GHz/sec"), duration=t01 * u.ns) # f01 MHz -> (f01 + 10)MHz
        # play("const" * amp(1.0), "col_selector_01", chirp=(50, "GHz/sec")) # f01 MHz -> (f01 + 10)MHz
        # play("const" * amp(0.9), "col_selector_01", chirp=(60, "GHz/sec")) # f01 MHz -> (f01 + 10)MHz
        # play("const" * amp(1.0), "col_selector_01", chirp=([100, 105, 110], "GHz/sec"), duration=t01 * u.ns) # f01 MHz -> (f01 + 10)MHz

        with infinite_loop_():
            for i in range(n_tweezers):
                r = (i + 1) / n_tweezers
                play("const" * amp(r), f"col_selector_{i + 1:02d}")
                play("const" * amp(r), f"row_selector_{i + 1:02d}")

    #####################################
    #  Open Communication with the QOP  #
    #####################################

    job = qmm.simulate(config, PROG, SimulationConfig(200))
    samples = job.get_simulated_samples()
    samples.con1.plot()
    plt.show()
    import time; time.sleep(5);
    instance.close()

# %%
