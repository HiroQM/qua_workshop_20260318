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
    #   QUA Program   #
    ###################

    n_avg = 100  # The number of averages
    elem = "detector"

    with program() as PROG:
        n = declare(int)  # QUA variable for the averaging loop
        adc_st = declare_stream(adc_trace=True)  # The stream to store the raw ADC trace

        with for_(n, 0, n < n_avg, n + 1):
            # External trigger input receives triggers from an external instrument
            wait_for_trigger(elem)
            # Sends the readout pulse and stores the raw ADC traces in the stream called "adc_st"
            # Latency between the external trigger and measurement should be calibrated and update `time_of_flight`
            measure("readout", elem, adc_st)
            # Wait for saving
            wait(10 * u.us)

        with stream_processing():
            if config["elements"]["detector"]["outputs"]["out1"][1] == 1:
                # Will save average:
                adc_st.input1().average().save(f"adc")
                # Will save only last run:
                adc_st.input1().save(f"adc_single_run")
            else:
                # Will save average:
                adc_st.input2().average().save(f"adc")
                # Will save only last run:
                adc_st.input2().save(f"adc_single_run")

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
