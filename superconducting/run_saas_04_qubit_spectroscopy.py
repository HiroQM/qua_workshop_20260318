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
    # Adjust the pulse duration and amplitude to drive the qubit into a mixed state
    saturation_len = 10 * u.us  # In ns
    saturation_amp = 0.5  # pre-factor to the value defined in the config - restricted to [-2; 2)
    # Qubit detuning sweep
    center = 0 * u.MHz
    span = 10 * u.MHz
    df = 100 * u.kHz
    dfs = np.arange(-span, +span + 0.1, df)

    ###################
    # The QUA program #
    ###################
    with program() as qubit_spec:
        n = declare(int)  # QUA variable for the averaging loop
        df = declare(int)  # QUA variable for the qubit frequency
        I = declare(fixed)  # QUA variable for the measured 'I' quadrature
        Q = declare(fixed)  # QUA variable for the measured 'Q' quadrature
        I_st = declare_stream()  # Stream for the 'I' quadrature
        Q_st = declare_stream()  # Stream for the 'Q' quadrature
        n_st = declare_stream()  # Stream for the averaging iteration 'n'

        # Adjust the flux line if needed
        # set_dc_offset("flux_line", "single", 0.0)
        with for_(n, 0, n < n_avg, n + 1):
            with for_(*from_array(df, dfs)):
                # Update the frequency of the digital oscillator linked to the qubit element
                update_frequency("qubit", df + center)
                # Play the saturation pulse to put the qubit in a mixed state - Can adjust the amplitude on the fly [-2; 2)
                play("saturation" * amp(saturation_amp), "qubit", duration=saturation_len * u.ns)
                # Align the two elements to measure after playing the qubit pulse.
                # One can also measure the resonator while driving the qubit by commenting the 'align'
                align("qubit", "resonator")
                # Measure the state of the resonator
                measure(
                    "readout",
                    "resonator",
                    None,
                    dual_demod.full("cos", "sin", I),
                    dual_demod.full("minus_sin", "cos", Q),
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
            I_st.buffer(len(dfs)).average().save("I")
            Q_st.buffer(len(dfs)).average().save("Q")
            n_st.save("iteration")

    #####################################
    #  Open Communication with the QOP  #
    #####################################

    job = qmm.simulate(config, qubit_spec, SimulationConfig(200))
    samples = job.get_simulated_samples()
    samples.con1.plot()
    plt.show()
    import time; time.sleep(5);
    instance.close()

# %%

