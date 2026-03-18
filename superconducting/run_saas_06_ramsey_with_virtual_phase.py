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
    n_avg = 1000
    # Dephasing time sweep (in clock cycles = 4ns) - minimum is 4 clock cycles
    tau_min = 4
    tau_max = 2000 // 4
    d_tau = 40 // 4
    taus = np.arange(tau_min, tau_max + 0.1, d_tau)  # + 0.1 to add tau_max to taus
    # Detuning converted into virtual Z-rotations to observe Ramsey oscillation and get the qubit frequency
    detuning = 1 * u.MHz  # in Hz

    ###################
    # The QUA program #
    ###################
    with program() as ramsey:
        n = declare(int)  # QUA variable for the averaging loop
        tau = declare(int)  # QUA variable for the idle time
        phase = declare(fixed)  # QUA variable for dephasing the second pi/2 pulse (virtual Z-rotation)
        I = declare(fixed)  # QUA variable for the measured 'I' quadrature
        Q = declare(fixed)  # QUA variable for the measured 'Q' quadrature
        state = declare(bool)  # QUA variable for the qubit state
        I_st = declare_stream()  # Stream for the 'I' quadrature
        Q_st = declare_stream()  # Stream for the 'Q' quadrature
        state_st = declare_stream()  # Stream for the qubit state
        n_st = declare_stream()  # Stream for the averaging iteration 'n'

        with for_(n, 0, n < n_avg, n + 1):
            with for_(*from_array(tau, taus)):
                # Rotate the frame of the second x90 gate to implement a virtual Z-rotation
                # 4*tau because tau was in clock cycles and 1e-9 because tau is ns
                assign(phase, Cast.mul_fixed_by_int(detuning * 1e-9, 4 * tau))
                # 1st x90 gate
                play("x90", "qubit")
                # Wait a varying idle time
                wait(tau, "qubit")
                # Rotate the frame of the second x90 gate to implement a virtual Z-rotation
                frame_rotation_2pi(phase, "qubit")
                # 2nd x90 gate
                play("x90", "qubit")
                # Align the two elements to measure after playing the qubit pulse.
                align("qubit", "resonator")
                # Measure the state of the resonator
                measure(
                    "readout",
                    "resonator",
                    None,
                    dual_demod.full("rotated_cos", "rotated_sin", I),
                    dual_demod.full("rotated_minus_sin", "rotated_cos", Q),
                )
                # Wait for the qubit to decay to the ground state
                wait(thermalization_time * u.ns, "resonator")
                # State discrimination
                assign(state, I > ge_threshold)
                # Save the 'I', 'Q' and 'state' to their respective streams
                save(I, I_st)
                save(Q, Q_st)
                save(state, state_st)
                # Reset the frame of the qubit in order not to accumulate rotations
                reset_frame("qubit")
            # Save the averaging iteration to get the progress bar
            save(n, n_st)

        with stream_processing():
            # Cast the data into a 1D vector, average the 1D vectors together and store the results on the OPX processor
            I_st.buffer(len(taus)).average().save("I")
            Q_st.buffer(len(taus)).average().save("Q")
            state_st.boolean_to_int().buffer(len(taus)).average().save("state")
            n_st.save("iteration")


    #####################################
    #  Open Communication with the QOP  #
    #####################################

    job = qmm.simulate(config, ramsey, SimulationConfig(200))
    samples = job.get_simulated_samples()
    samples.con1.plot()
    plt.show()
    import time; time.sleep(5);
    instance.close()

# %%

