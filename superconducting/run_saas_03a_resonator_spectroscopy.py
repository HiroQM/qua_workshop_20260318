# %%
from qm import QuantumMachinesManager
from qm.qua import *
from qm import SimulationConfig, LoopbackInterface
from qualang_tools.loops import from_array
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

    ##################
    #   Parameters   #
    ##################
    # Parameters Definition
    n_avg = 100  # The number of averages
    # The frequency sweep parameters
    f_min = 30 * u.MHz
    f_max = 70 * u.MHz
    df = 100 * u.kHz
    frequencies = np.arange(f_min, f_max + 0.1, df)  # The frequency vector (+ 0.1 to add f_max to frequencies)

    ###################
    # The QUA program #
    ###################
    with program() as resonator_spec:
        n = declare(int)  # QUA variable for the averaging loop
        f = declare(int)  # QUA variable for the readout frequency
        I = declare(fixed)  # QUA variable for the measured 'I' quadrature
        Q = declare(fixed)  # QUA variable for the measured 'Q' quadrature
        I_st = declare_stream()  # Stream for the 'I' quadrature
        Q_st = declare_stream()  # Stream for the 'Q' quadrature
        n_st = declare_stream()  # Stream for the averaging iteration 'n'
        
        with for_(n, 0, n < n_avg, n + 1):  # QUA for_ loop for averaging
            
            with for_(*from_array(f, frequencies)):  # QUA for_ loop for sweeping the frequency
                # Update the frequency of the digital oscillator linked to the resonator element
                update_frequency("resonator", f)
                # Measure the resonator (send a readout pulse and demodulate the signals to get the 'I' & 'Q' quadratures)
                measure(
                    "readout",
                    "resonator",
                    None,
                    dual_demod.full("cos", "sin", I),
                    dual_demod.full("minus_sin", "cos", Q),
                )
                # Wait for the resonator to deplete
                wait(100 * u.ns, "resonator")
                # Save the 'I' & 'Q' quadratures to their respective streams
                save(I, I_st)
                save(Q, Q_st)
            # Save the averaging iteration to get the progress bar
            save(n, n_st)

        with stream_processing():
            # Cast the data into a 1D vector, average the 1D vectors together and store the results on the OPX processor
            n_st.save("iteration")
            I_st.buffer(len(frequencies)).average().save("I")
            Q_st.buffer(len(frequencies)).average().save("Q")

    #####################################
    #  Open Communication with the QOP  #
    #####################################

    job = qmm.simulate(config, resonator_spec, SimulationConfig(200))
    samples = job.get_simulated_samples()
    samples.con1.plot()
    plt.show()
    import time; time.sleep(5);
    instance.close()

# %%

