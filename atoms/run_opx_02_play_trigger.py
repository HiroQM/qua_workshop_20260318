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
    
    with infinite_loop_():
        play("on", "trigger_artiq")
        wait(250)


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