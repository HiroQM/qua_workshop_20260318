
# Single QUA script generated at 2026-04-22 08:13:05.031176
# QUA library version: 1.2.6


from qm import CompilerOptionArguments
from qm.qua import *

with program() as prog:
    a1 = declare(int, size=120)
    a2 = declare(int, value=[0, 0, 0, 0])
    a3 = declare(int, size=256)
    v1 = declare(fixed, )
    v2 = declare(fixed, )
    v3 = declare(fixed, value=1.0)
    v4 = declare(fixed, value=1.0)
    v5 = declare(fixed, )
    v6 = declare(fixed, )
    v7 = declare(fixed, value=1.0)
    v8 = declare(fixed, value=1.0)
    v9 = declare(fixed, value=-2.0)
    v10 = declare(int, value=0)
    v11 = declare(int, value=0)
    v12 = declare(int, value=0)
    v13 = declare(bool, value=True)
    v14 = declare(fixed, )
    v15 = declare(int, )
    v16 = declare(int, )
    v17 = declare(int, )
    v18 = declare(int, )
    v19 = declare(int, )
    v20 = declare(int, value=0)
    v21 = declare(int, )
    v22 = declare(int, )
    v23 = declare(int, )
    v24 = declare(int, )
    v25 = declare(int, )
    with while_(v13):
        align()
        measure("read", "lfm3_in_ch2", integration.full("constant", v1, "out1"))
        measure("read", "lfm3_in_ch1", integration.full("constant", v5, "out1"))
        assign(v2, Util.cond((v1>0),1.0,0.0))
        assign(v4, (Util.cond((v3<v2),1.0,0.0)-Util.cond((v2<v3),1.0,0.0)))
        assign(v3, v2)
        assign(v6, Util.cond((v5>0),1.0,0.0))
        assign(v8, (Util.cond((v7<v6),1.0,0.0)-Util.cond((v6<v7),1.0,0.0)))
        assign(v7, v6)
        with if_((v9==-2)):
            with if_(((v2==0)&(v8==1))):
                assign(v9, -1)
        with else_():
            with if_(((v2==0)&(v8==-1))):
                assign(v9, -2)
                assign(v13, False)
            with elif_((v4==-1)):
                assign(v9, Util.cond((v6==1),0.0,1.0))
                with if_((v9==1.0)):
                    with if_((v12<8)):
                        assign(v11, (v11+(128>>v12)))
                    with else_():
                        assign(a3[v10], (v12-8))
                        assign(v10, (v10+1))
                assign(v12, (v12+1))
        align()
        r1 = declare_stream()
        save(v1, r1)
        r2 = declare_stream()
        save(v5, r2)
        r3 = declare_stream()
        save(v9, r3)
        # # add this to simulate
        # assign(v13, False)
    align()
    play("const", "chirp1", duration=16)
    align()
    with if_(((v10>=2)&(v10<=60))):
        assign(v14, (2/v10))
        align()
        assign(v15, (v10/2))
        with for_(v21,0,(v21<30),(v21+1)):
            assign(v22, ((4*v21)+0))
            assign(v23, ((4*v21)+1))
            assign(v24, ((4*v21)+2))
            assign(v25, ((4*v21)+3))
            with if_((v10>(2*v21))):
                assign(v16, ((a3[(v21+v15)]-a3[v21])*299791))
                assign(a1[v22], v16)
                assign(v17, ((a3[(v21+v15)]-a3[v21])*1148257))
                assign(a1[v23], v17)
                assign(v18, ((a3[(v21+v15)]-a3[v21])*1148257))
                assign(a1[v24], v18)
                assign(v19, ((a3[(v21+v15)]-a3[v21])*299791))
                assign(a1[v25], v19)
            with else_():
                assign(a1[v22], 0.0)
                assign(a1[v23], 0.0)
                assign(a1[v24], 0.0)
                assign(a1[v25], 0.0)
        for k in range(30):
            update_frequency(f"chirp{k + 1}", (55000000+(a3[k]*300000)), "Hz", False)
        align()
        assign(v19, 1024)
        for k in range(4):
            assign(a2[k], a1[k])
        play("const", "chirp1", duration=1024, chirp=(a2,None,"uHz/nsec"))
        align()
    align()
    r4 = declare_stream()
    save(v11, r4)
    r5 = declare_stream()
    save(v10, r5)
    with for_(v20,0,(v20<v10),(v20+1)):
        r6 = declare_stream()
        save(a3[v20], r6)
    with stream_processing():
        r1.save_all("clock_stream")
        r2.save_all("datach_stream")
        r3.save_all("datavisual")
        r4.save_all("col")
        r5.save_all("locsSize")
        r6.save_all("locs")

config = {
    "controllers": {
        "con1": {
            "type": "opx1000",
            "fems": {
                "1": {
                    "type": "LF",
                    "analog_outputs": {
                        "2": {
                            "offset": 0.0,
                            "sampling_rate": 1000000000.0,
                            "upsampling_mode": "mw",
                        },
                    },
                },
                "2": {
                    "type": "LF",
                    "analog_outputs": {
                        "2": {
                            "offset": 0.0,
                            "sampling_rate": 1000000000.0,
                            "upsampling_mode": "mw",
                        },
                    },
                },
                "3": {
                    "type": "LF",
                    "analog_outputs": {
                        "7": {
                            "offset": 0.0,
                        },
                    },
                    "analog_inputs": {
                        "1": {
                            "offset": 0.0,
                        },
                        "2": {
                            "offset": 0.0,
                        },
                    },
                    "digital_outputs": {
                        "1": {},
                    },
                },
            },
        },
    },
    "elements": {
        "chirp1": {
            "singleInput": {
                "port": ['con1', 2, 2],
            },
            "operations": {
                "const": "chirp_base_pulse",
            },
            "intermediate_frequency": 0,
            "core": "fem2-01",
        },
        "chirp2": {
            "singleInput": {
                "port": ['con1', 1, 2],
            },
            "operations": {
                "const": "chirp_base_pulse",
            },
            "intermediate_frequency": 0,
            "core": "fem1-01",
        },
        "chirp3": {
            "singleInput": {
                "port": ['con1', 2, 2],
            },
            "operations": {
                "const": "chirp_base_pulse",
            },
            "intermediate_frequency": 0,
            "core": "fem2-02",
        },
        "chirp4": {
            "singleInput": {
                "port": ['con1', 1, 2],
            },
            "operations": {
                "const": "chirp_base_pulse",
            },
            "intermediate_frequency": 0,
            "core": "fem1-02",
        },
        "chirp5": {
            "singleInput": {
                "port": ['con1', 2, 2],
            },
            "operations": {
                "const": "chirp_base_pulse",
            },
            "intermediate_frequency": 0,
            "core": "fem2-03",
        },
        "chirp6": {
            "singleInput": {
                "port": ['con1', 1, 2],
            },
            "operations": {
                "const": "chirp_base_pulse",
            },
            "intermediate_frequency": 0,
            "core": "fem1-03",
        },
        "chirp7": {
            "singleInput": {
                "port": ['con1', 2, 2],
            },
            "operations": {
                "const": "chirp_base_pulse",
            },
            "intermediate_frequency": 0,
            "core": "fem2-04",
        },
        "chirp8": {
            "singleInput": {
                "port": ['con1', 1, 2],
            },
            "operations": {
                "const": "chirp_base_pulse",
            },
            "intermediate_frequency": 0,
            "core": "fem1-04",
        },
        "chirp9": {
            "singleInput": {
                "port": ['con1', 2, 2],
            },
            "operations": {
                "const": "chirp_base_pulse",
            },
            "intermediate_frequency": 0,
            "core": "fem2-05",
        },
        "chirp10": {
            "singleInput": {
                "port": ['con1', 1, 2],
            },
            "operations": {
                "const": "chirp_base_pulse",
            },
            "intermediate_frequency": 0,
            "core": "fem1-05",
        },
        "chirp11": {
            "singleInput": {
                "port": ['con1', 2, 2],
            },
            "operations": {
                "const": "chirp_base_pulse",
            },
            "intermediate_frequency": 0,
            "core": "fem2-06",
        },
        "chirp12": {
            "singleInput": {
                "port": ['con1', 1, 2],
            },
            "operations": {
                "const": "chirp_base_pulse",
            },
            "intermediate_frequency": 0,
            "core": "fem1-06",
        },
        "chirp13": {
            "singleInput": {
                "port": ['con1', 2, 2],
            },
            "operations": {
                "const": "chirp_base_pulse",
            },
            "intermediate_frequency": 0,
            "core": "fem2-07",
        },
        "chirp14": {
            "singleInput": {
                "port": ['con1', 1, 2],
            },
            "operations": {
                "const": "chirp_base_pulse",
            },
            "intermediate_frequency": 0,
            "core": "fem1-07",
        },
        "chirp15": {
            "singleInput": {
                "port": ['con1', 2, 2],
            },
            "operations": {
                "const": "chirp_base_pulse",
            },
            "intermediate_frequency": 0,
            "core": "fem2-08",
        },
        "chirp16": {
            "singleInput": {
                "port": ['con1', 1, 2],
            },
            "operations": {
                "const": "chirp_base_pulse",
            },
            "intermediate_frequency": 0,
            "core": "fem1-08",
        },
        "chirp17": {
            "singleInput": {
                "port": ['con1', 2, 2],
            },
            "operations": {
                "const": "chirp_base_pulse",
            },
            "intermediate_frequency": 0,
            "core": "fem2-09",
        },
        "chirp18": {
            "singleInput": {
                "port": ['con1', 1, 2],
            },
            "operations": {
                "const": "chirp_base_pulse",
            },
            "intermediate_frequency": 0,
            "core": "fem1-09",
        },
        "chirp19": {
            "singleInput": {
                "port": ['con1', 2, 2],
            },
            "operations": {
                "const": "chirp_base_pulse",
            },
            "intermediate_frequency": 0,
            "core": "fem2-10",
        },
        "chirp20": {
            "singleInput": {
                "port": ['con1', 1, 2],
            },
            "operations": {
                "const": "chirp_base_pulse",
            },
            "intermediate_frequency": 0,
            "core": "fem1-10",
        },
        "chirp21": {
            "singleInput": {
                "port": ['con1', 2, 2],
            },
            "operations": {
                "const": "chirp_base_pulse",
            },
            "intermediate_frequency": 0,
            "core": "fem2-11",
        },
        "chirp22": {
            "singleInput": {
                "port": ['con1', 1, 2],
            },
            "operations": {
                "const": "chirp_base_pulse",
            },
            "intermediate_frequency": 0,
            "core": "fem1-11",
        },
        "chirp23": {
            "singleInput": {
                "port": ['con1', 2, 2],
            },
            "operations": {
                "const": "chirp_base_pulse",
            },
            "intermediate_frequency": 0,
            "core": "fem2-12",
        },
        "chirp24": {
            "singleInput": {
                "port": ['con1', 1, 2],
            },
            "operations": {
                "const": "chirp_base_pulse",
            },
            "intermediate_frequency": 0,
            "core": "fem1-12",
        },
        "chirp25": {
            "singleInput": {
                "port": ['con1', 2, 2],
            },
            "operations": {
                "const": "chirp_base_pulse",
            },
            "intermediate_frequency": 0,
            "core": "fem2-13",
        },
        "chirp26": {
            "singleInput": {
                "port": ['con1', 1, 2],
            },
            "operations": {
                "const": "chirp_base_pulse",
            },
            "intermediate_frequency": 0,
            "core": "fem1-13",
        },
        "chirp27": {
            "singleInput": {
                "port": ['con1', 2, 2],
            },
            "operations": {
                "const": "chirp_base_pulse",
            },
            "intermediate_frequency": 0,
            "core": "fem2-14",
        },
        "chirp28": {
            "singleInput": {
                "port": ['con1', 1, 2],
            },
            "operations": {
                "const": "chirp_base_pulse",
            },
            "intermediate_frequency": 0,
            "core": "fem1-14",
        },
        "chirp29": {
            "singleInput": {
                "port": ['con1', 2, 2],
            },
            "operations": {
                "const": "chirp_base_pulse",
            },
            "intermediate_frequency": 0,
            "core": "fem2-15",
        },
        "chirp30": {
            "singleInput": {
                "port": ['con1', 1, 2],
            },
            "operations": {
                "const": "chirp_base_pulse",
            },
            "intermediate_frequency": 0,
            "core": "fem1-15",
        },
        "lfm1_out": {
            "singleInput": {
                "port": ('con1', 1, 2),
            },
            "operations": {
                "const": "const_pulse",
            },
        },
        "lfm2_out": {
            "singleInput": {
                "port": ('con1', 2, 2),
            },
            "operations": {
                "const": "const_pulse",
            },
        },
        "lfm3_in_ch1": {
            "singleInput": {
                "port": ('con1', 3, 7),
            },
            "intermediate_frequency": 0,
            "operations": {
                "read": "read_pulse",
            },
            "outputs": {
                "out1": ('con1', 3, 1),
            },
            "time_of_flight": 28,
            "smearing": 0,
        },
        "lfm3_in_ch2": {
            "singleInput": {
                "port": ('con1', 3, 7),
            },
            "intermediate_frequency": 0,
            "operations": {
                "read": "read_pulse",
            },
            "outputs": {
                "out1": ('con1', 3, 2),
            },
            "time_of_flight": 28,
            "smearing": 0,
        },
    },
    "pulses": {
        "const_pulse": {
            "operation": "control",
            "length": 80,
            "waveforms": {
                "single": "const_wf",
            },
        },
        "chirp_base_pulse": {
            "operation": "control",
            "length": 414400,
            "waveforms": {
                "single": "const_wf",
            },
        },
        "read_pulse": {
            "operation": "measurement",
            "length": 80,
            "waveforms": {
                "single": "zero_wf",
            },
            "integration_weights": {
                "constant": "constant_weights",
            },
            "digital_marker": "ON",
        },
    },
    "waveforms": {
        "const_wf": {
            "type": "constant",
            "sample": 0.4,
        },
        "zero_wf": {
            "type": "constant",
            "sample": 0.0,
        },
    },
    "digital_waveforms": {
        "ON": {
            "samples": [(1, 0)],
        },
    },
    "integration_weights": {
        "constant_weights": {
            "cosine": [(1.0, 80)],
            "sine": [(0.0, 80)],
        },
    },
}


#####################################
#             Imports               #
#####################################

from qm_saas import QOPVersion, QmSaas
import matplotlib.pyplot as plt
from qm import LoopbackInterface, QuantumMachinesManager, SimulationConfig
from qm.qua import *

#####################################
#  Open Communication with the QOP  #
#####################################
QOP_VER = "v3_6_2"
HOST = "qm-saas.quantum-machines.co"
EMAIL = None # 
PWD = None # 
QOP_IP = None # 
CLUSTER_NAME = None # 

use_saas = True

if use_saas:
    # Initialize QOP simulator client
    client = QmSaas(email=EMAIL, password=PWD, host=HOST)
    print(f"Latest QOP: {client.latest_version()}")

    with client.simulator(QOPVersion(QOP_VER)) as instance:
        # Initialize QuantumMachinesManager with the simulation instance details
        qmm = QuantumMachinesManager(
            host=instance.host,
            port=instance.port,
            connection_headers=instance.default_connection_headers,
        )

        from qm import generate_qua_script
        sourceFile = open("debug_saas.py", 'w')
        print(generate_qua_script(prog, config), file=sourceFile) 
        sourceFile.close()

        # Open a quantum machine to execute the QUA program
        qm = qmm.open_qm(config, close_other_machines=True)
        # Send the QUA program to the OPX, which compiles and executes it
        job = qm.execute(prog)

else:
    #####################################
    #  Open Communication with the QOP  #
    #####################################

    qmm = QuantumMachinesManager(host=QOP_IP, cluster_name=CLUSTER_NAME)

    from qm import generate_qua_script
    sourceFile = open("debug.py", 'w')
    print(generate_qua_script(prog, config), file=sourceFile) 
    sourceFile.close()

    # Open a quantum machine to execute the QUA program
    qm = qmm.open_qm(config, close_other_machines=True)
    # Send the QUA program to the OPX, which compiles and executes it
    job = qm.execute(prog)
    # Creates a result handle to fetch data from the OPX
    res_handles = job.result_handles
    # Waits (blocks the Python console) until all results have been acquired
    res_handles.wait_for_all_values()
    # Prints the fetched results
    for w in ["clock_stream", "datach_stream", "datavisual", "col", "locsSize", "locs"]:
        w_ = res_handles.get(w).fetch_all()
        print(f"{w} = {w_}")

    qm.close()

#%%