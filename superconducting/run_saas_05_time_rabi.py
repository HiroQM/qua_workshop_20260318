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
    # Pulse duration sweep (in clock cycles = 4ns)
    # must be larger than 4 clock cycles and larger than the pi_len defined in the config
    t_min = 16 // 4
    t_max = 2000 // 4
    dt = 4 // 4
    durations = np.arange(t_min, t_max, dt)

    ###################
    # The QUA program #
    ###################
    with program() as time_rabi:
        n = declare(int)  # QUA variable for the averaging loop
        t = declare(int)  # QUA variable for the qubit pulse duration
        I = declare(fixed)  # QUA variable for the measured 'I' quadrature
        Q = declare(fixed)  # QUA variable for the measured 'Q' quadrature
        I_st = declare_stream()  # Stream for the 'I' quadrature
        Q_st = declare_stream()  # Stream for the 'Q' quadrature
        n_st = declare_stream()  # Stream for the averaging iteration 'n'

        with for_(n, 0, n < n_avg, n + 1):  # QUA for_ loop for averaging
            with for_(*from_array(t, durations)):  # QUA for_ loop for sweeping the pulse duration
                # Play the qubit pulse with a variable duration (in clock cycles = 4ns)
                play("x180", "qubit", duration=t)
                # Align the two elements to measure after playing the qubit pulse.
                align("qubit", "resonator")
                # Measure the state of the resonator
                # The integration weights have changed to maximize the SNR after having calibrated the IQ blobs.
                measure(
                    "readout",
                    "resonator",
                    None,
                    dual_demod.full("rotated_cos", "rotated_sin", I),
                    dual_demod.full("rotated_minus_sin", "rotated_cos", Q),
                )
                # Wait for the qubit to decay to the ground state
                wait(thermalization_time * u.ns, "resonator")
                # Save the 'I' & 'Q' quadratures to their respective streams
                save(I, I_st)
                save(Q, Q_st)
            # Save the averaging iteration to get the progress bar
            save(n, n_st)

        with stream_processing():
            # Cast the data into a 1D vector, average the 1D vectors together and store the results on the OPX processor
            I_st.buffer(len(durations)).average().save("I")
            Q_st.buffer(len(durations)).average().save("Q")
            n_st.save("iteration")

    #####################################
    #  Open Communication with the QOP  #
    #####################################

    job = qmm.simulate(config, time_rabi, SimulationConfig(200))
    samples = job.get_simulated_samples()
    samples.con1.plot()
    plt.show()
    import time; time.sleep(5);
    instance.close()

# %%

