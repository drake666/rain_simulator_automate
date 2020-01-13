import pexpect
from pexpect.popen_spawn import PopenSpawn
from shutil import copyfile
import os
import time
import threading
import sys
import signal
import numpy as np
import json
from simulation import *
from nusc_dataset import NuScenesDataset, ImageFolder

weathers = []
for fallrate in [100]: #5, 17, 25, 50, 75, 100, 200, 300, 400]:
    weathers.append({"weather": "rain", "fallrate": fallrate})

with open("v1.0-trainval_both_nnight_nrain_val.json") as f:
    tokens = json.load(f)["sample_data_tokens"]

nusc = NuScenesDataset(version="v1.0-trainval", root="/data/nuscenes",
                       specific_tokens=tokens,
                       only_annotated=False)
cameras = nusc.estimate_camera_settings("CAM_FRONT")
motions = nusc.estimate_camera_motions("CAM_FRONT")
durations = nusc.estimate_sequences_duration("CAM_FRONT")
scene_tokens = list(set(nusc.scene_tokens))

sequences = []
for t in scene_tokens:
    sequences.append(["nuscenes_2Hz", t, cameras[t], motions[t], durations[t]])
# sequences.append(["nuscenes_2Hz", scene_tokens[0], cameras[scene_tokens[0]], [[0, 0, 0] for _ in range(40)], 40 * 0.5])
# sequences.append(["nuscenes_2Hz", scene_tokens[1], cameras[scene_tokens[1]], [[0, 0, 0] for _ in range(40)], 40 * 0.5])


# addhoc nuscenes (yeah, just to know how many image... stupid, I know)
# adhoc = ImageFolder(root="input/GAN")
# adhoc_camera = cameras[list(scene_tokens)[0]]
# img = adhoc[0]
# adhoc_camera["height"] = img.shape[0]
# adhoc_camera["width"] = img.shape[1]
# sequences.append(["nuscenes", "__adhoc__", adhoc_camera, [[0, 0, 1.157]], 1 + len(adhoc) / 12])

#sequences.append(["kitti", "0000"])
#sequences.append(["kitti", "0032"])
#sequences.append(["kitti", "0056"])
#sequences.append(["kitti", "0071"])
#sequences.append(["kitti", "0117"])

max_thread = 10
window_mode = False
threads = np.array([], object)
for weather in weathers:
    for sequence in sequences:
        print("Create thread: ", sequence[:2], weather)
        sim = WeatherSimulation(sequence, weather, window_mode)
        threads = np.append(threads, sim)


while len(threads) > 0:
    thread_not_started_mask = np.array([not t._started.is_set() for t in threads])

    if np.sum(thread_not_started_mask) > 0:
        t = threads[thread_not_started_mask][0]
        print("START thread: ", t.sequence[:2], t.weather)
        t.start()
        # to ensure that the seed (which seems to use the time in sec :| ?!) won't be the same
        time.sleep(1.5)

    # Wait for an available thread
    print("Wait for threads")
    while np.sum([t.isAlive() for t in threads]) >= max_thread:
        time.sleep(2)

    thread_ended_mask = np.array([not t.isAlive() and t._started.is_set() for t in threads])
    for t in threads[thread_ended_mask]:
        print("Thread ended: ", t.sequence[:2], t.weather)
    threads = threads[~thread_ended_mask]

    # Wait for all threads if no remaining ones
    if np.sum(np.array([not t._started.is_set() for t in threads])) == 0:
        while np.sum([t.isAlive() for t in threads]) != 0:
            time.sleep(2)

        print("All threads completed")
