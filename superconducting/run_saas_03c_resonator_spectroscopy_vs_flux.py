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
    n_avg = 6000  # Number of averaging loops
    # The frequency sweep around the resonator frequency "resonator_IF"
    span = 10 * u.MHz
    df = 100 * u.kHz
    dfs = np.arange(-span, +span + 0.1, df)
    # Flux bias sweep in V
    flux_min = -0.49
    flux_max = 0.49
    step = 0.01
    flux = np.arange(flux_min, flux_max + step / 2, step)

    ###################
    # The QUA program #
    ###################
    with program() as resonator_spec_flux:
        n = declare(int)  # QUA variable for the averaging loop
        f = declare(int)  # QUA variable for the readout frequency
        dc = declare(fixed)  # QUA variable for the flux bias
        I = declare(fixed)  # QUA variable for the measured 'I' quadrature
        Q = declare(fixed)  # QUA variable for the measured 'Q' quadrature
        I_st = declare_stream()  # Stream for the 'I' quadrature
        Q_st = declare_stream()  # Stream for the 'Q' quadrature
        n_st = declare_stream()  # Stream for the averaging iteration 'n'

        with for_(n, 0, n < n_avg, n + 1):
            with for_(*from_array(f, dfs)):
                # Update the frequency of the digital oscillator linked to the resonator element
                update_frequency("resonator", f + resonator_IF)
                with for_(*from_array(dc, flux)):
                    # Flux sweeping by tuning the OPX dc offset associated to the flux_line element
                    set_dc_offset("flux_line", "single", dc)
                    wait(flux_settle_time * u.ns, "resonator", "qubit")
                    # Measure the resonator (send a readout pulse whose amplitude is rescaled by the pre-factor 'a' [-2, 2)
                    # and demodulate the signals to get the 'I' & 'Q' quadratures)
                    measure(
                        "readout",
                        "resonator",
                        None,
                        dual_demod.full("cos", "sin", I),
                        dual_demod.full("minus_sin", "cos", Q),
                    )
                    # Wait for the resonator to cooldown
                    wait(depletion_time * u.ns, "resonator")
                    # Save the 'I' & 'Q' quadratures to their respective streams
                    save(I, I_st)
                    save(Q, Q_st)
            # Save the averaging iteration to get the progress bar
            save(n, n_st)

        with stream_processing():
            # Cast the data into a 2D matrix, average the 2D matrices together and store the results on the OPX processor
            I_st.buffer(len(flux)).buffer(len(dfs)).average().save("I")
            Q_st.buffer(len(flux)).buffer(len(dfs)).average().save("Q")
            n_st.save("iteration")


    #####################################
    #  Open Communication with the QOP  #
    #####################################

    job = qmm.simulate(config, resonator_spec_flux, SimulationConfig(200))
    samples = job.get_simulated_samples()
    samples.con1.plot()
    plt.show()
    import time; time.sleep(5);
    instance.close()

# %%

