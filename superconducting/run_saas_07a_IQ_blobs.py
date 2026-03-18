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
    n_shot = 10000  # Number of acquired shots
    # The thresholds ar calibrated with the IQ_blobs.py script:
    # If I > threshold_e, then the qubit is assumed to be in |e> and a pi pulse is played to reset it.
    # If I < threshold_g, then the qubit is assumed to be in |g>.
    # else, the qubit state is not determined accurately enough, so we just measure again.

    ###################
    # The QUA program #
    ###################
    with program() as active_reset:
        n = declare(int)  # Averaging index
        I = declare(fixed)
        Q = declare(fixed)
        I_st = declare_stream()
        Q_st = declare_stream()
        I_g = declare(fixed)
        Q_g = declare(fixed)
        I_g_st = declare_stream()
        Q_g_st = declare_stream()
        I_e = declare(fixed)
        Q_e = declare(fixed)
        I_e_st = declare_stream()
        Q_e_st = declare_stream()

        with for_(n, 0, n < n_shot, n + 1):
            # Measure the state of the resonator, qubit should be in |g>
            measure(
                "readout",
                "resonator",
                None,
                dual_demod.full("rotated_cos", "rotated_sin", I_g),
                dual_demod.full("rotated_minus_sin", "rotated_cos", Q_g),
            )
            # Save the 'I' & 'Q' quadratures to their respective streams for the ground state
            save(I_g, I_g_st)
            save(Q_g, Q_g_st)
            wait(depletion_time * u.ns, "resonator")

            # global align
            align()

            # Play the x180 gate to put the qubit in the excited state
            play("x180", "qubit")
            # Align the two elements to measure after playing the qubit pulse.
            align("qubit", "resonator")
            # Measure the state of the resonator, qubit should be in |e>
            measure(
                "readout",
                "resonator",
                None,
                dual_demod.full("rotated_cos", "rotated_sin", I_e),
                dual_demod.full("rotated_minus_sin", "rotated_cos", Q_e),
            )
            # Save the 'I' & 'Q' quadratures to their respective streams for the excited state
            save(I_e, I_e_st)
            save(Q_e, Q_e_st)
            wait(depletion_time * u.ns, "resonator")

        with stream_processing():
            # Save all streamed points for plotting the IQ blobs
            I_g_st.save_all("I_g")
            Q_g_st.save_all("Q_g")
            I_e_st.save_all("I_e")
            Q_e_st.save_all("Q_e")

    #####################################
    #  Open Communication with the QOP  #
    #####################################

    job = qmm.simulate(config, active_reset, SimulationConfig(200))
    samples = job.get_simulated_samples()
    samples.con1.plot()
    plt.show()
    import time; time.sleep(5);
    instance.close()

# %%

