# %%
from qm import QuantumMachinesManager
from qm.qua import *
from qm import SimulationConfig, LoopbackInterface
# from configuration_opxplus_octave import *
from configuration_opx1000_lffem import *
import matplotlib.pyplot as plt
from qm_saas import QOPVersion, QmSaas


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

    num_sites = num_cols * num_rows
    threshold = 0.1

    with program() as PROG:
        n = declare(int)  # Counter for keeping track of the received locations
        I = declare(fixed)  # integrated I for occupation matrix readout
        occupation_matrix = declare(bool)  # Full 1D occupation matrix
        occupation_matrix_st = declare_stream()

        with for_(n, 0, n < num_sites, n + 1):
            wait_for_trigger("detector")
            wait(1 * u.us, "detector") # Need a calibraiton for the latency
            measure(
                "readout",
                "detector",
                integration.full("const", I, "out1"),
            )

            assign(occupation_matrix, I < threshold)
            save(occupation_matrix, occupation_matrix_st)
            wait(250)

        with stream_processing():
            occupation_matrix_st.boolean_to_int().buffer(num_sites).save("occupation_matrix")
    
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
