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
    
    def active_reset_one_threshold(threshold_g: float, max_tries: int):
        """
        Active reset protocol where the outcome of the measurement is compared to a pre-calibrated threshold (IQ_blobs.py).
        If the qubit is in |e> (I>threshold), then play a pi pulse and measure again, else (qubit in |g>) return the number
        of pi-pulses needed to reset the qubit.
        The program waits for the resonator to deplete before playing the conditional pi-pulse so that the calibrated
        pi-pulse parameters are still valid.

        :param threshold_g: threshold between the |g> and |e> blobs - calibrated in IQ_blobs.py
        :param max_tries: maximum number of iterations needed to reset the qubit before exiting the loop anyway.
        :return: the number of tries to reset the qubit.
        """
        I_reset = declare(fixed)
        counter = declare(int)
        assign(counter, 0)
        align("resonator", "qubit")
        with while_((I_reset > threshold_g) & (counter < max_tries)):
            # Measure the state of the resonator
            measure("readout", "resonator", None, dual_demod.full("rotated_cos", "rotated_sin", I_reset))
            align("resonator", "qubit")
            # Wait for the resonator to deplete
            wait(depletion_time * u.ns, "qubit")
            # Play a conditional pi-pulse to actively reset the qubit
            play("x180", "qubit", condition=(I_reset > threshold_g))
            # Update the counter for benchmarking purposes
            assign(counter, counter + 1)
        return counter

    ##################
    #   Parameters   #
    ##################
    # Parameters Definition
    n_shot = 10000  # Number of acquired shots
    # The thresholds ar calibrated with the IQ_blobs.py script:
    # If I > threshold_e, then the qubit is assumed to be in |e> and a pi pulse is played to reset it.
    # If I < threshold_g, then the qubit is assumed to be in |g>.
    # else, the qubit state is not determined accurately enough, so we just measure again.
    ge_threshold_g = ge_threshold * 0.5
    ge_threshold_e = ge_threshold
    # Maximum number of tries for active reset
    max_tries = 2

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
            # Active reset
            count = active_reset_one_threshold(threshold_g=ge_threshold_g, max_tries=max_tries)
            align()
            # Measure the state of the resonator after reset, qubit should be in |g>
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

            # global align
            align()

            # Active reset
            count = active_reset_one_threshold(threshold_g=ge_threshold_g, max_tries=max_tries)
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

