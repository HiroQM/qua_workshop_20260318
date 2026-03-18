# %%
from qm import QuantumMachinesManager
from qm.qua import *
from qm import SimulationConfig, LoopbackInterface
from qualang_tools.loops import from_array
from qualang_tools.bakery.randomized_benchmark_c1 import c1_table
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
    
    def power_law(power, a, b, p):
        return a * (p**power) + b


    def generate_sequence():
        cayley = declare(int, value=c1_table.flatten().tolist())
        inv_list = declare(int, value=inv_gates)
        current_state = declare(int)
        step = declare(int)
        sequence = declare(int, size=max_circuit_depth + 1)
        inv_gate = declare(int, size=max_circuit_depth + 1)
        i = declare(int)
        rand = Random(seed=seed)

        assign(current_state, 0)
        with for_(i, 0, i < max_circuit_depth, i + 1):
            assign(step, rand.rand_int(24))
            assign(current_state, cayley[current_state * 24 + step])
            assign(sequence[i], step)
            assign(inv_gate[i], inv_list[current_state])

        return sequence, inv_gate


    def play_sequence(sequence_list, depth):
        i = declare(int)
        with for_(i, 0, i <= depth, i + 1):
            with switch_(sequence_list[i], unsafe=True):
                with case_(0):
                    wait(x180_len // 4, "qubit")
                with case_(1):
                    play("x180", "qubit")
                with case_(2):
                    play("y180", "qubit")
                with case_(3):
                    play("y180", "qubit")
                    play("x180", "qubit")
                with case_(4):
                    play("x90", "qubit")
                    play("y90", "qubit")
                with case_(5):
                    play("x90", "qubit")
                    play("-y90", "qubit")
                with case_(6):
                    play("-x90", "qubit")
                    play("y90", "qubit")
                with case_(7):
                    play("-x90", "qubit")
                    play("-y90", "qubit")
                with case_(8):
                    play("y90", "qubit")
                    play("x90", "qubit")
                with case_(9):
                    play("y90", "qubit")
                    play("-x90", "qubit")
                with case_(10):
                    play("-y90", "qubit")
                    play("x90", "qubit")
                with case_(11):
                    play("-y90", "qubit")
                    play("-x90", "qubit")
                with case_(12):
                    play("x90", "qubit")
                with case_(13):
                    play("-x90", "qubit")
                with case_(14):
                    play("y90", "qubit")
                with case_(15):
                    play("-y90", "qubit")
                with case_(16):
                    play("-x90", "qubit")
                    play("y90", "qubit")
                    play("x90", "qubit")
                with case_(17):
                    play("-x90", "qubit")
                    play("-y90", "qubit")
                    play("x90", "qubit")
                with case_(18):
                    play("x180", "qubit")
                    play("y90", "qubit")
                with case_(19):
                    play("x180", "qubit")
                    play("-y90", "qubit")
                with case_(20):
                    play("y180", "qubit")
                    play("x90", "qubit")
                with case_(21):
                    play("y180", "qubit")
                    play("-x90", "qubit")
                with case_(22):
                    play("x90", "qubit")
                    play("y90", "qubit")
                    play("x90", "qubit")
                with case_(23):
                    play("-x90", "qubit")
                    play("y90", "qubit")
                    play("-x90", "qubit")

    ##################
    #   Parameters   #
    ##################
    # Parameters Definition
    num_of_sequences = 20  # Number of random sequences
    n_avg = 20  # Number of averaging loops for each random sequence
    max_circuit_depth = 100  # Maximum circuit depth
    delta_clifford = 10  # Play each sequence with a depth step equals to 'delta_clifford - Must be > 0
    assert (max_circuit_depth / delta_clifford).is_integer(), "max_circuit_depth / delta_clifford must be an integer."
    seed = 345324  # Pseudo-random number generator seed

    # List of recovery gates from the lookup table
    inv_gates = [int(np.where(c1_table[i, :] == 0)[0][0]) for i in range(24)]

    ###################
    # The QUA program #
    ###################
    with program() as rb1q:
        depth = declare(int)  # QUA variable for the varying depth
        depth_target = declare(int)  # QUA variable for the current depth (changes in steps of delta_clifford)
        # QUA variable to store the last Clifford gate of the current sequence which is replaced by the recovery gate
        saved_gate = declare(int)
        m = declare(int)  # QUA variable for the loop over random sequences
        n = declare(int)  # QUA variable for the averaging loop
        I = declare(fixed)  # QUA variable for the 'I' quadrature
        Q = declare(fixed)  # QUA variable for the 'Q' quadrature
        state = declare(bool)  # QUA variable for state discrimination
        # The relevant streams
        m_st = declare_stream()
        state_st = declare_stream()

        with for_(m, 0, m < num_of_sequences, m + 1):  # QUA for_ loop over the random sequences
            sequence_list, inv_gate_list = generate_sequence()  # Generate the random sequence of length max_circuit_depth

            assign(depth_target, 1)  # Initialize the current depth to 1
            with for_(depth, 1, depth <= max_circuit_depth, depth + 1):  # Loop over the depths
                # Replacing the last gate in the sequence with the sequence's inverse gate
                # The original gate is saved in 'saved_gate' and is being restored at the end
                assign(saved_gate, sequence_list[depth])
                assign(sequence_list[depth], inv_gate_list[depth - 1])
                # Only played the depth corresponding to target_depth
                with if_(depth == depth_target):
                    with for_(n, 0, n < n_avg, n + 1):  # Averaging loop
                        # Can be replaced by active reset
                        wait(thermalization_time * u.ns, "resonator")
                        # Align the two elements to play the sequence after qubit initialization
                        align("resonator", "qubit")
                        # Play the random sequence of desired depth
                        play_sequence(sequence_list, depth)
                        # Align the two elements to measure after playing the circuit.
                        align("qubit", "resonator")
                        # Make sure you updated the ge_threshold and angle if you want to use state discrimination
                        measure(
                            "readout",
                            "resonator",
                            None,
                            dual_demod.full("rotated_cos", "rotated_sin", I),
                            dual_demod.full("rotated_minus_sin", "rotated_cos", Q),
                        )
                        assign(state, I > ge_threshold)
                        save(state, state_st)
                    # Go to the next depth
                    assign(depth_target, depth_target + delta_clifford)
                # Reset the last gate of the sequence back to the original Clifford gate
                # (that was replaced by the recovery gate at the beginning)
                assign(sequence_list[depth], saved_gate)
            # Save the counter for the progress bar
            save(m, m_st)

        with stream_processing():
            m_st.save("iteration")
            # returns a 1D array of averaged random pulse sequences vs depth of circuit for live plotting
            state_st.boolean_to_int().buffer(n_avg).map(FUNCTIONS.average()).buffer(max_circuit_depth / delta_clifford).average().save("state_avg")

    #####################################
    #  Open Communication with the QOP  #
    #####################################

    job = qmm.simulate(config, rb1q, SimulationConfig(1000))
    samples = job.get_simulated_samples()
    samples.con1.plot()
    plt.show()
    import time; time.sleep(5);
    instance.close()

# %%

