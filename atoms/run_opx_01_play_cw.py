# %%
import matplotlib.pyplot as plt
from configuration_opx1000_mwfem_lffem import *
from qm import LoopbackInterface, QuantumMachinesManager, SimulationConfig
from qm.qua import *
from qualang_tools.loops import from_array
from qualang_tools.plot import interrupt_on_close
from qualang_tools.results import fetching_tool, progress_counter
from qualang_tools.results.data_handler import DataHandler

save_data_dict = {
    "config": config,
}


###################
# The QUA program #
###################

with program() as PROG:
        
    # # case1
    # play("const", "col_selector_01") # 100MHz, 1us

    # # case2
    # play("const", "col_selector_01", chirp=(100, "GHz/sec")) # 100MHz -> 120MHz

    # # case3
    # update_frequency("col_selector_01", 80 * u.MHz)
    # play("const", "col_selector_01") # 80MHz, 1us

    # # case4
    # update_frequency("col_selector_01", 80 * u.MHz)
    # play("const", "col_selector_01", chirp=(100, "GHz/sec")) # 80MHz -> 100MHz

    # # case5
    # # f01 = 75MHz # QUA variable on FPGA
    # update_frequency("col_selector_01", f01)
    # play("const", "col_selector_01", chirp=(100, "GHz/sec")) # f01 MHz -> (f01 + 20)MHz

    # # case6
    # # f01 = 75MHz # QUA variable on FPGA
    # # t01 = 500 ns # QUA variable on FPGA
    # update_frequency("col_selector_01", f01)
    # play("const", "col_selector_01", chirp=(100, "GHz/sec"), duration=t01 * u.ns) # f01 MHz -> (f01 + 10)MHz
    # play("const" * amp(1.0), "col_selector_01", chirp=(50, "GHz/sec")) # f01 MHz -> (f01 + 10)MHz
    # play("const" * amp(0.9), "col_selector_01", chirp=(60, "GHz/sec")) # f01 MHz -> (f01 + 10)MHz
    # play("const" * amp(1.0), "col_selector_01", chirp=([100, 105, 110], "GHz/sec"), duration=t01 * u.ns) # f01 MHz -> (f01 + 10)MHz

    with infinite_loop_():
        for i in range(n_tweezers):
            r = (i + 1) / n_tweezers
            play("const" * amp(r), f"col_selector_{i + 1:02d}")
            play("const" * amp(r), f"row_selector_{i + 1:02d}")


#####################################
#  Open Communication with the QOP  #
#####################################
qmm = QuantumMachinesManager(host=QOP_IP, cluster_name=CLUSTER_NAME)


#######################
# Simulate or execute #
#######################
simulate = False

if simulate:
    # Simulates the QUA program for the specified duration
    simulation_config = SimulationConfig(duration=1_000)  # In clock cycles = 4ns
    # Simulate blocks python until the simulation is done
    job = qmm.simulate(config, PROG, simulation_config)
    # Get the simulated samples
    samples = job.get_simulated_samples()
    # Plot the simulated samples
    samples.con1.plot()
    # Get the waveform report object
    waveform_report = job.get_simulated_waveform_report()
    # Cast the waveform report to a python dictionary
    waveform_dict = waveform_report.to_dict()
    # Visualize and save the waveform report
    waveform_report.create_plot(samples, plot=True, save_path=str(Path(__file__).resolve()))

else:
    # Open the quantum machine
    qm = qmm.open_qm(config, close_other_machines=True)
    # Send the QUA program to the OPX, which compiles and executes it
    job = qm.execute(PROG)
    import time;time.sleep(5)
    qm.close()

    # Save results
    script_path = Path(__file__)
    data_handler = DataHandler(root_data_folder=save_dir_atoms)
    data_handler.create_data_folder(name=Path(__file__).stem)
    data_handler.additional_files = {script_path: script_path.name, **default_additional_files_atoms}
    data_handler.save_data(data=save_data_dict, name=Path(__file__).stem)

    # Generate serialized program
    from qm import generate_qua_script
    sourceFile = open(data_handler.path / f'debug_{Path(__file__).stem}.py', 'w')
    print(generate_qua_script(PROG, config), file=sourceFile) 
    sourceFile.close()

#%%