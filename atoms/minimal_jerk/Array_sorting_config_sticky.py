from qm.qua import *
import numpy as np
import time
from qm.QuantumMachinesManager import QuantumMachinesManager
import matplotlib.pyplot as plt


def Blackman(T,v_start,v_end): # The Blackman pulse, minimizes the ammount of side lobes in the FT\n",
        time=np.asarray([x*1.0 for x in range(int(T))])
        Black = v_start+(time/T-(25/(42*np.pi))*np.sin(2*np.pi*time/T)+(1/(21*np.pi))*np.sin(4*np.pi*time/T))*(v_end-v_start)
        return Black

def Transport_Pulse(element, chirp_iterations, chirp_rate, AOM_original_IF):
    reset_phase(element)
    update_frequency(element, AOM_original_IF)
    play('Blackman_up', element)
    for i in range(chirp_iterations):
        play('Constant', element, chirp=(chirp_rate, 'Hz/nsec'))
    #update_frequency(element, AOM_original_IF+chirp_iterations*chirp_rate*Single_tone_length)
    play('Constant', element, chirp=(0, 'Hz/nsec')) #Blackman_down

def Play_Multi_Tone():
    #align(['Tweezer_{}'.format(x) for x in range(1,10)])
    for element in ['Tweezer_{}'.format(x) for x in range(1,10)]:
        play('Constant', element)




Phases_List = [0.9611612 , 0.28973053, 0.19682382, 0.43125266, 0.4918641 , 0.37902614, 0.56157891, 0.82004078, 0.7420598]


AOM_IF=50e6

#Integration_Weights_Length = 1000000
flag_digital = 1

Number_of_tweezers = 18
Blackman_pulse_length = 25000
Blackman_Amp = 0.49/Number_of_tweezers

ms = 1e6
Blackman_long_pulse_length = 0.05*ms
Sampling_Rate = 100e6

Single_tone_Amp = 0.49/Number_of_tweezers
#Single_tone_length = 16
#Short_pulse_length = 288+96 #336 #356 #484
Single_tone_length = 684
Short_pulse_length = 16

ramp_length = 400e3/4 # ramp length = 300 microseconds in clock cycles
ramp_slope = Single_tone_Amp / ramp_length / 4 # the ramp slope in V/ns

Digital_inputs_delay = 136
Digital_inputs_buffer = 0
Trigger_length = 1000
Integration_Weights_Length = 1000

Row_selector_voltage_offset = 0.0
Tweezer_selector_voltage_offset = 0.0
Row_selector_IF = 120e6
Row_Spacing = 1.6e6
N_Rows = 16

Tweezer_Spacing = 1.6e6 # in Hz
Atom_Spacing = 5 #in um
N_Tweezer_Grid_Size = 30
Tweezer_IF_First_Site = 89.2e6
Tweezer_IF = [int(Tweezer_IF_First_Site+Tweezer_Spacing*i) for i in range(N_Tweezer_Grid_Size)]
Tweezer_idle_Frequency = 1e6


Max_Detuning = Tweezer_IF[-1] - Tweezer_IF[0]
Max_Rate = 1e-5*(Tweezer_Spacing/Atom_Spacing) #10 um/ms = 10*1e-6 um/ns = 10*1e-6*(1.6e6/5)~3.2 Hz/ns = 3200 mHz/ns
#OneOver_Max_Rate = 1/Max_Rate

Readout_pulse_length = Single_tone_length + 2*Blackman_long_pulse_length

TOF_delay_PHD = 0
Tweezer_Channel = 3
Row_Channel = 4

Row_Trigger_Channel = 2
Tweezer_Trigger_Channel = 1
config = {
    'version': 1,

    'controllers': {
        'con1': {
            'type': 'opx1',
            'analog_outputs': {
                Row_Channel: {'offset': Row_selector_voltage_offset}, # Row AOD tone
                Tweezer_Channel: {'offset': Tweezer_selector_voltage_offset}, # Tweezer AOD tone
                #9: {'offset': 0.0},
                #10: {'offset': 0.0}
            },
            'digital_outputs': {
                1: {}, # Row Trigger Channel
                2: {}, # Tweezers Trigger Channel
                3: {}, # Recorder Trigger
            },
            'analog_inputs': {
                1: {'offset': 0.0},  # Photodiode 1
                2: {'offset': 0.0},  # Photodiode 2
            },
        },
    },

    'elements': {



        'Row_selector': {
            'singleInput': {
                'port': ('con1', Row_Channel),
            },
            'intermediate_frequency': Row_selector_IF,
            'operations': {
                'Blackman_up': 'Blackman_up_pulse',
                'Blackman_down': 'Blackman_down_pulse',
                'Blackman_up_long': 'Blackman_up_long_pulse',
                'Blackman_down_long': 'Blackman_down_long_pulse',
                'Constant': 'Constant_pulse',
                'Constant_short': 'Constant_short',
                'Zero_amplitude': 'Zero_amplitude',
                'Single_tone': 'Single_tone_pulse',
                'Readout': 'Readout_pulse',
            },
            'digitalInputs': {
                'Row_switch': {
                    'port': ('con1', Row_Trigger_Channel),
                    'delay': Digital_inputs_delay,
                    'buffer': Digital_inputs_buffer,
                },
            },
            'outputs': {
                'out1': ('con1', 1)
            },
            'time_of_flight': 28 + TOF_delay_PHD,
            'smearing': 0,
        },

        **{f'Tweezer_{i+1}': {
            'singleInput': {
                'port': ('con1', Tweezer_Channel),
            },
            'intermediate_frequency': Tweezer_idle_Frequency,
            'operations': {
                'Blackman_up': 'Blackman_up_pulse', # play('readout', 'Resonator')
                'Blackman_down': 'Blackman_down_pulse',
                'Blackman_down_negative': 'Blackman_down_pulse_negative',
                'Blackman_up_long': 'Blackman_up_long_pulse',
                'Blackman_down_long': 'Blackman_down_long_pulse',
                'Constant': 'Constant_pulse',
                'Constant_short': 'Constant_short',
                'Zero_amplitude': 'Zero_amplitude',
                'Single_tone': 'Single_tone_pulse'
            },
            'hold_offset': {'duration': 1},
            'digitalInputs': {
                'Tweezer_switch': {
                    'port': ('con1', Tweezer_Trigger_Channel),
                    'delay': Digital_inputs_delay,
                    'buffer': Digital_inputs_buffer,
                },
            },
        } for i in range(Number_of_tweezers)},


    },

    "pulses": {
        'Trigger_pulse': {
            'operation': 'control',
            'length': Trigger_length,
            'digital_marker': 'Trigger_digital_train',
        },

        'Readout_pulse': {
            'operation': 'measurement',
            'length': Readout_pulse_length,
            'waveforms': {
                'single': 'zero_wf',
            },
            'integration_weights': {
                'integW_cos': 'integW_cosine',
                'integW_sin': 'integW_sine',
            },
            'digital_marker': 'ON',

        },

        'Blackman_up_pulse': {
            'operation': 'control',
            'length': Blackman_pulse_length,
            'waveforms': {
                'single': 'Blackman_up_wf',
            },
            'digital_marker': 'ON',
        },
        'Blackman_down_pulse': {
            'operation': 'control',
            'length': Blackman_pulse_length,
            'waveforms': {
                'single': 'Blackman_down_wf',
            },
            'digital_marker': 'ON',
        },
        'Blackman_down_pulse_negative': {
            'operation': 'control',
            'length': Blackman_pulse_length,
            'waveforms': {
                'single': 'Blackman_down_negative_wf',
            },
            'digital_marker': 'ON',
        },

        'Blackman_up_long_pulse': {
            'operation': 'control',
            'length': Blackman_long_pulse_length,
            'waveforms': {
                'single': 'Blackman_up_long_wf',
            },
            'digital_marker': 'ON',
        },

        'Blackman_down_long_pulse': {
            'operation': 'control',
            'length': Blackman_long_pulse_length,
            'waveforms': {
                'single': 'Blackman_down_long_wf',
            },
            'digital_marker': 'ON',
        },

        'Constant_pulse': {
            'operation': 'control',
            'length': Single_tone_length,
            'waveforms': {
                'single': 'Constant_wf',
            },
            'digital_marker': 'ON',
        },
        'Constant_short': {
            'operation': 'control',
            'length': Short_pulse_length,
            'waveforms': {
                'single': 'Constant_wf',
            },
            'digital_marker': 'ON',
        },
        'Zero_amplitude': {
            'operation': 'control',
            'length': Short_pulse_length,
            'waveforms': {
                'single': 'zero_wf',
            },
            'digital_marker': 'ON',
        },
        'Single_tone_pulse': {
            'operation': 'control',
            'length': Single_tone_length,
            'waveforms': {
                'single': 'Single_tone_wf',
            },
            'digital_marker': 'ON',
        },

    },

    'waveforms': {

        'Blackman_up_wf': {
            'type': 'arbitrary',
            'samples': Blackman(Blackman_pulse_length, 0, Blackman_Amp),
        },
        'Blackman_down_wf': {
            'type': 'arbitrary',
            'samples': Blackman(Blackman_pulse_length, Blackman_Amp, 0),
        },
        'Blackman_down_negative_wf': {
            'type': 'arbitrary',
            'samples': Blackman(Blackman_pulse_length, 0, -Blackman_Amp),
        },
        'Blackman_up_long_wf': {
            'type': 'arbitrary',
            'samples': Blackman(Blackman_long_pulse_length/(1e9/Sampling_Rate), 0, Blackman_Amp),
            'sampling_rate': Sampling_Rate
        },
        'Blackman_down_long_wf': {
            'type': 'arbitrary',
            'samples': Blackman(Blackman_long_pulse_length/(1e9/Sampling_Rate), Blackman_Amp, 0),
            'sampling_rate': Sampling_Rate,
        },
        'Constant_wf': {
            'type': 'constant',
            'sample': Single_tone_Amp,
        },
        'Single_tone_wf': {
            'type': 'constant',
            'sample': Single_tone_Amp
        },
        'zero_wf': {
            'type': 'constant',
            'sample': 0.0,
        },
    },

    'digital_waveforms': {

        'ON': {
            'samples': [(flag_digital, 0)]
        },

        'OFF': {
            'samples': [(0, 0)]
        },

        'Trigger_digital_train': {
            'samples': [(1,Trigger_length/2), (0,0)]
        },
    },

    'integration_weights': {

        'integW_cosine': {
            'cosine': [1.0] * int(Integration_Weights_Length / 4),
            'sine': [0.0] * int(Integration_Weights_Length / 4),
        },

        'integW_sine': {
            'cosine': [0.0] * int(Integration_Weights_Length / 4),
            'sine': [1.0] * int(Integration_Weights_Length / 4),
        },

    },

}