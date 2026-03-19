# %%
from qm import QuantumMachinesManager
from qm.qua import *
from qm import SimulationConfig, LoopbackInterface
import matplotlib.pyplot as plt
from qm_saas import QOPVersion, QmSaas

from configuration_opx1000_mwfem_lffem import *


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

        with infinite_loop_():
            # play('pulse', 'qe', chirp=(rate, units))
            # units are 'Hz/nsec', 'mHz/nsec', 'uHz/nsec', 'pHz/nsec'
            # or 'GHz/sec', 'MHz/sec', 'KHz/sec', 'Hz/sec', 'mHz/sec'. 
            play("const", "col_selector_01", chirp=(+2e6, "GHz/sec"))
            play("const", "col_selector_01", chirp=(-2e6, "GHz/sec"))
            wait(250)
    
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
