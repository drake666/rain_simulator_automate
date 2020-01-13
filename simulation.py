import pexpect
from pexpect.popen_spawn import PopenSpawn
from shutil import copyfile
import os
import time
import threading
import sys
import signal
import numpy as np
from pexpect.exceptions import ExceptionPexpect

class logwriter():
    def __init__(self, outbuffer):
        self._outbuffer = outbuffer

    def write(self, str):
        self._outbuffer.write(str.decode('ascii'))

    def flush(self):
        self._outbuffer.flush()


sequence_code = {}
sequence_code["kitti"] = "80"
sequence_code["cityscape"] = "90"


class WeatherSimulation(threading.Thread):
    def __init__(self, sequence, weather, window_mode=True):
        threading.Thread.__init__(self)

        self.sequence = sequence
        self.weather = weather
        self.window_mode = window_mode

    def run(self, redo=False):
        sequence = self.sequence
        weather = self.weather

        output_dir = os.path.join(os.getcwd(), 'output', sequence[0], sequence[1],
                                  "%s_%smm" % (weather["weather"], str(weather["fallrate"])))
        os.makedirs(output_dir, exist_ok=True)

        # Yeah, perhaps I don't want to redo everything...
        if not redo:
            files = os.listdir(output_dir)
            results_computed = np.any(["fps_camera0.xml" in f for f in files])
            if results_computed:
                return

        logfile = open(os.path.join(output_dir, 'automate_log.txt'), 'a+')
        child = PopenSpawn('bin/AHLSimulation.exe', cwd=output_dir, logfile=logwriter(logfile))

        try:
            print(" In main menu")
            child.expect('What do you want to do \?')

            if sequence[0] in sequence_code:
                child.sendline('99'.encode('ascii'))
                time.sleep(0.5)

                print(" Setting system")
                child.expect('Which system to run ?')
                seq_code = sequence_code[sequence[0]]+sequence[1]
                print('		System code: ', seq_code)
                child.sendline(seq_code.encode('ascii'))
            elif "nuscenes" in sequence[0].lower():
                child.sendline('99'.encode('ascii'))
                time.sleep(0.5)

                print(" Setting system")
                child.expect('Which system to run ?')
                if "2Hz" in sequence[0]:
                    seq_code = '1000'
                else:
                    seq_code = '100'
                print('		System code: ', seq_code)
                child.sendline(seq_code.encode('ascii'))
            else:
                raise NotImplementedError("No settings for this set {}".format(sequence[0]))

            # Deactivate windows AND save light map option (I was lazy that day)
            if not self.window_mode:
                print(" In main menu")
                child.expect('What do you want to do \?')
                child.sendline('28'.encode('ascii'))
                time.sleep(0.5)
                print("	Save light map")

            # Deactivate rain particles
            print(" Deactivating rain particles")
            child.expect('What do you want to do \?')
            child.sendline('410'.encode('ascii'))
            child.expect('410. Rain \(OFF\)')

            if weather["weather"] == "rain":
                print(" Activating rain particles")
                # Activate rain particles
                child.expect('What do you want to do \?')
                child.sendline('410'.encode('ascii'))
                child.expect('410. Rain \(ON\)')

                print(" Setting rain fallrate")
                # Set rain fallrate
                child.expect('What do you want to do \?')
                child.sendline('414'.encode('ascii'))

                child.expect('Enter new Rain fall rate')
                code = str(weather["fallrate"])
                print(" Send: ", code)
                child.sendline(code.encode('ascii'))

            # if sequence[0].lower() == "nuscenes":
            #     print(" In main menu")
            #     print(" Starting simulation")
            #     child.expect('What do you want to do \?')
            #     child.sendline('1'.encode('ascii'))
            #
            #     child.expect('\[Simulation stopped\]', timeout=None)
            #     print(" Simulation stopped")
            #     time.sleep(5.)  # Wait for the "Press any key to continue"
            #     child.sendline(b'\n')
            # else:
            print(" In main menu")
            print(" Going to step menu")
            child.expect('What do you want to do \?')
            child.sendline('102'.encode('ascii'))

            if "nuscenes" in sequence[0].lower():
                child.expect('Steps: What do you want to do \?')
                print(" In Step menu")
                child.sendline('18'.encode('ascii'))
                print(" Camera 0 motion speed choices")
                child.expect("What do you want to do")
                child.sendline('3'.encode('ascii'))
                print("		Camera 0 motion speed choices (3 -> all at once)")

                speed = np.linalg.norm(np.array(sequence[3]), axis=1) / 1000 * 3600 / (np.array(sequence[4]) * 1e-6)
                child.expect("Separator")
                child.sendline(';'.encode('ascii'))
                child.expect("Enter all steps values")
                print("		Camera 0 motion speed min, max: {}, {}".format(np.min(speed), np.max(speed)))
                child.sendline(';'.join([str(s) for s in speed.tolist()]).encode('ascii'))
                child.expect("Continue")
                child.sendline('y'.encode('ascii'))

            child.expect('Steps: What do you want to do \?')
            print(" In Step menu")
            print(" Starting simulation")
            child.sendline('1'.encode('ascii'))

            child.expect('\[Simulation stopped\]', timeout=None)
            print(" Simulation stopped")
            time.sleep(5.)  # Wait for t    he "Press any key to continue"
            child.sendline(b'\n')

            child.expect('Steps: What do you want to do \?')
            print(" In Step menu")
            print(" Going to main menu")
            child.sendline('0'.encode('ascii'))

            print(" In main menu")
            print(" Stopping process")
            child.expect('What do you want to do \?')
            child.sendline('0'.encode('ascii'))

            child.expect('Press any key to continue . . .')
            child.sendline(b'\n')
            child.expect('Press any key to continue . . .')
            child.sendline(b'\n')

            child.wait()
            child.kill(signal.CTRL_C_EVENT)

            logfile.close()
        except ExceptionPexpect as e:
            print(e)
            child.kill(signal.CTRL_C_EVENT)