from qm.QuantumMachinesManager import QuantumMachinesManager
from qm import SimulationConfig
from Array_sorting_config_sticky import *
from qm.simulate.credentials import create_credentials

#################################
# This function moves atoms in 1D with a minimal jerk. It divides the path to N segments and calculate the
# frequency chirp and the amplitude ramp in each segment.
#################################


### Open communication with Quantum Machine
qmm = QuantumMachinesManager()
# qm = qmm.open_qm(config, close_other_machines=True)


### pythonic variables
max_number_of_tweezers = 18


### function that moves the atoms
# 1. Initialize each tweezer
# 2. play Blackman-up pulse for each tweezer
# 3. calcualte the chirp rate and amplitude ramp and play a ramp pulse with frequency chirping for each segment seperately
def move_atoms_1D(number_of_tweezers, initial_frequencies, detunings, initial_phases, segment_length, chirp_N_segments):
    coef = declare(fixed) # coefficient for easier calculations
    t_c = declare(fixed)
    t_c_squared = declare(fixed)

    assign(coef, 30000 / (segment_length * chirp_N_segments)) #  30 times 1000 in order to change the chirp rate to mHz

    # Initialization for each tweezer:
    for index in range(number_of_tweezers):

        # change the frequency of each tweezer to be in GHz
        assign(f[index], Cast.mul_fixed_by_int(1e-6, Cast.mul_int_by_fixed(initial_frequencies[index], 1e-3)))  # frequency in GHz

        # set amplitude as a function of frequency
        assign(amplitude[index], Cast.mul_fixed_by_int((f[index] * f[index] - 0.2481199407 * f[index] + 0.01569066401) * (f[index] * f[index] - 0.16721839647 * f[index] + 0.007299457367388), 1738801))

        # set the ramp_rate to be zero
        assign(ramp_rates[index], 0.0)

        #  update the initial frequency
        update_frequency('Tweezer_{}'.format(index+1), initial_frequencies[index]) # in Hz

        # update the initial phase
        frame_rotation_2pi(initial_phases[index], 'Tweezer_{}'.format(index + 1))

    align()

    # play Blackman-up pulse for each tweezer
    for index in range(number_of_tweezers):
        play('Blackman_up'*amp(amplitude[index]), 'Tweezer_{}'.format(index+1))

    with for_(t_c, 1/chirp_N_segments, t_c<1, t_c+1/chirp_N_segments):
        # play a ramp pulse while the chirp was calculated before with continue_chirp=True
        for index in range(number_of_tweezers):
            play(ramp(ramp_rates[index]), 'Tweezer_{}'.format(index+1), duration=(segment_length-32)/4) # time to calculate all the below calculation 16ns for the chirp pulse (at the end of the outer loop), 16 for loop t_c

        assign(t_c_squared, t_c*t_c)

        # Per tweezer:
        # 1. Calculate frequency
        # 2. Calculate chirp rate
        # 3. Calculate ramp rate
        for index in range(number_of_tweezers):

            # calculate chirp rate according to the formula in the article
            assign(chirp_rates[index], Cast.mul_int_by_fixed(detunings[index], coef*t_c_squared*(1 - 2*t_c + t_c_squared)))

            # calculate frequency at the end of the segment using the chirp rate and segment length
            assign(f[index], f[index] + segment_length * 1e-5 * Cast.mul_fixed_by_int(1e-7, chirp_rates[
                index]))  # frequency in GHz

            # Calculate ramp rate
            assign(ramp_rates[index], 1e-7*Cast.mul_fixed_by_int(1.6e-6,Cast.mul_int_by_fixed(chirp_rates[index],Cast.mul_fixed_by_int((f[index]-0.1144836367)*(f[index]-0.10294187)*(f[index]-0.094078247),434700+21300))))#6955206


        for index in range(number_of_tweezers):
            # The first play for the next segment with continue_chirp=True
            play(ramp(ramp_rates[index]), 'Tweezer_{}'.format(index + 1), duration=4, chirp=(chirp_rates[index], 'mHz/nsec'), continue_chirp=True)

    # Play Blackman-down pulse for each tweezer
    for index in range(number_of_tweezers):
        play('Zero_amplitude', 'Tweezer_{}'.format(index + 1), continue_chirp=False) # top chirping..

        assign(f[index], f[index] + segment_length*1e-5 * Cast.mul_fixed_by_int(1e-7, chirp_rates[index]))
        # Calculate the relevant amplitude for the Blackman-down pulse
        assign(amplitude[index], Cast.mul_fixed_by_int((f[index] * f[index] - 0.2481199407 * f[index] + 0.01569066401) * (f[index] * f[index] - 0.16721839647 * f[index] + 0.007299457367388), 1738801))
        play('Blackman_down_negative'*amp(amplitude[index]), 'Tweezer_{}'.format(index+1))
        ramp_to_zero('Tweezer_{}'.format(index+1))


### QUA program
with program() as minimal_jerk:

    f = [declare(fixed, value=0) for i in range(max_number_of_tweezers)]  # declare frequencies in Hz (will be converted to GHz)

    initial_frequencies = [declare(int, value=int(10e6 + i * 10e6)) for i in range(max_number_of_tweezers)]  # declare initial frequencies Hz
    initial_phases = [declare(fixed, value=0.002 * np.pi * i ** 3) for i in range(max_number_of_tweezers)]  # declare initial phases

    detunings = [declare(int, value=int((i ** 2 + 1) * 0.5e6)) for i in range(max_number_of_tweezers)]  # declare detunings in Hz
    chirp_rates = [declare(int, value=0) for i in range(max_number_of_tweezers)]  # declare chirp rates in mHz/nsec

    amplitude = [declare(fixed, value=0) for i in range(max_number_of_tweezers)]  # declare amplitudes
    ramp_rates = [declare(fixed, value=0) for i in range(max_number_of_tweezers)]  # declare ramp rates

    # chirp parameters
    chirp_N_segments = 1000  # number of segments
    segment_length = 800  # segment length in ns

    # defining random_atoms and detunings for simulation
    random_atoms = [int(x * 1e6) for x in
                    [85, 86, 87, 88, 89, 90, 91, 92, 93, 94]]     # making a random array of atoms (initial_frequencies for the move_atoms_1D function)
    detunings = [declare(int, value=int(85e6 + i * 2e6 - random_atoms[i])) for i in range(random_atoms.__len__())]
    # This will create 10 tweezers chirping from initial to final frequencies
    move_atoms_1D(random_atoms.__len__(), random_atoms, detunings, np.zeros(random_atoms.__len__()), segment_length, chirp_N_segments)
    # This will create a single tweezer chirping from 85 MHz to 120 MHz
    #move_atoms_1D(1, [85e6], [35e6], [0.0], segment_length, chirp_N_segments)  # simulating only one atom


### Execute or simulate the program

simulate = True
if simulate:

    simulation_duration = 250000
    job_sim = qmm.simulate(config, minimal_jerk, SimulationConfig(simulation_duration))
    samples = job_sim.get_simulated_samples()

    Port3 = samples.con1.analog['3']

    plt.figure(figsize=(7, 4))

    plt.plot(Port3)

    plt.grid()
    plt.show()

    plt.figure(figsize=(7, 4))
    powerSpectrum, freqenciesFound, time, imageAxis = plt.specgram(Port3, Fs=1e9, NFFT=4096, noverlap=1024)

    plt.xlabel('Time')

    plt.ylabel('Frequency')
    plt.ylim([80e6, 125e6])
    plt.show()

if not simulate:
    qm = qmm.open_qm(config, close_other_machines=True)
    job = qm.execute(minimal_jerk)