# %%
from qm import QuantumMachinesManager
from qm.qua import *
from qm import SimulationConfig, LoopbackInterface
# from configuration_opxplus_octave import *
from configuration_opx1000_mwfem_lffem import *
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

    n_avg = 100

    with program() as prog:
        n = declare(int)  # QUA variable for the averaging loop
        adc_st = declare_stream(adc_trace=True)  # The stream to store the raw ADC trace
        
        with for_(n, 0, n < n_avg, n + 1):  # QUA for_ loop for averaging
            # Make sure that the readout pulse is sent with the same phase so that the acquired signal does not average out
            reset_phase("resonator")
            # Measure the resonator (send a readout pulse and record the raw ADC trace)
            measure("readout", "resonator", adc_st)

        with stream_processing():
            # Will save average:
            adc_st.input1().average().save("adc1")
            # Will save only last run:
            adc_st.input1().save("adc1_single_run")

    #####################################
    #  Open Communication with the QOP  #
    #####################################

    job = qmm.simulate(config, prog, SimulationConfig(200))
    samples = job.get_simulated_samples()
    samples.con1.plot()
    plt.show()
    import time; time.sleep(5);
    instance.close()

# %%

