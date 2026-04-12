# %%
import matplotlib.pyplot as plt
from configuration_opx1000_mwfem_lffem import *
from qm import LoopbackInterface, QuantumMachinesManager
from qm.qua import *


###################
# The QUA program #
###################


with program() as PROG:
    
    m, m_st = declare(int, value=80), declare_stream()
    n, n_st = declare(int, value=100), declare_stream()
    a1, a1_st = declare(int), declare_stream()
    a2, a2_st = declare(int), declare_stream()
    v1, v1_st = declare(fixed), declare_stream()
    v2, v2_st = declare(fixed), declare_stream()
    v3, v3_st = declare(fixed), declare_stream()
    v4, v4_st = declare(fixed), declare_stream()

    save(m, m_st)
    save(n, n_st)

    # QUA int divisions returning fixed
    assign(v1, m / n)
    save(v1, v1_st)

    # QUA int divisions returning int
    assign(a1, m / n)
    save(a1, a1_st)

    # QUA int divisions with Math.div returning fixed
    assign(v2, Math.div(m, n))
    save(v2, v2_st)

    # QUA int divisions with Math.div returning int
    assign(a2, Math.div(m, n))
    save(a2, a2_st)

    # python literal
    assign(v3, 0.8)
    save(v3, v3_st)

    # python literal division
    assign(v4, 80 / 100)
    save(v4, v4_st)

    with stream_processing():
        m_st.save("m")
        n_st.save("n")
        a1_st.save("a1")
        a2_st.save("a2")
        v1_st.save("v1")
        v2_st.save("v2")
        v3_st.save("v3")
        v4_st.save("v4")


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
for w in ["m", "n", "a1", "v1", "a2", "v2", "v3", "v4"]:
    w_ = res_handles.get(w).fetch_all()
    print(f"{w} = {w_}")

qm.close()

#%%