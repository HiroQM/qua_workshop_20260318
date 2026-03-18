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

    elem = "col_selector_01"

    with program() as PROG:
        
        with infinite_loop_():
            play("const", elem)
            frame_rotation_2pi(0.25, elem) # apply pi/2 phase shift
            play("const", elem)

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
