# %%
import matplotlib.pyplot as plt
from configuration_opx1000_mwfem_lffem import *
from qm import LoopbackInterface, QuantumMachinesManager
from qm.qua import *


###################
# The QUA program #
###################


with program() as PROG:
    
    m, m_st = declare(int, value=77), declare_stream()
    n, n_st = declare(int, value=15), declare_stream()
    d, d_st = declare(int), declare_stream()
    a1, a1_st = declare(int), declare_stream()

    save(m, m_st)
    save(n, n_st)

    # QUA int divisions
    assign(d, Math.div(m, n)) # <- d = floor(m / n)
    assign(a1, m - n * d) # <- mod(m, n) = m - n * d
    save(a1, a1_st)

    with stream_processing():
        m_st.save("m")
        n_st.save("n")
        a1_st.save("a1")

#####################################
#  Open Communication with the QOP  #
#####################################
qmm = QuantumMachinesManager(host=QOP_IP, cluster_name=CLUSTER_NAME)

# Open a quantum machine to execute the QUA program
qm = qmm.open_qm(config, close_other_machines=True)
# Send the QUA program to the OPX, which compiles and executes it
job = qm.execute(PROG)
# Creates a result handle to fetch data from the OPX
res_handles = job.result_handles
# Waits (blocks the Python console) until all results have been acquired
res_handles.wait_for_all_values()
# Prints the fetched results
for w in ["m", "n", "a1"]:
    w_ = res_handles.get(w).fetch_all()
    print(f"{w} = {w_}")

qm.close()

#%%