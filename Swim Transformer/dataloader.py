import pandas as pd
import numpy as np
import os
import torch
from torch.utils.data import DataLoader
from sklearn.preprocessing import StandardScaler,MinMaxScaler

class TECDataset:
    def __init__(self, path, mode = 'maxmin', window_size = 24, patch_size = 3, input_history = 1) -> None:
        self.path = path
        self.window_size = window_size
        self.patch_size = patch_size * 8
        self.input_history = input_history
        self.val, self.val2 = 0, 0
        self.mode = "None"
        self.tec_data = self.get_data()
        if mode == 'maxmin':
            self.val, self.val2 = self.maxmin()
            self.mode = 'max_min'
        elif mode == 'z_score': #z_score
            self.val, self.val2 = self.z_scores()
            self.mode = 'z_score'
        self._input, self.target = self.create_dataset()
    
    #Let the data go through normalization
    def maxmin(self) :
        ma = max(self.tec_data)
        mi = min(self.tec_data)
        min_max_scaler = MinMaxScaler()
        self.tec_data = min_max_scaler.fit_transform(self.tec_data)
        return ma[0], mi[0]

    #Let the data go through standardization
    def z_scores(self) :
        standardizer  = StandardScaler()
        scaler = standardizer.fit(self.tec_data)
        self.tec_data = scaler.transform(self.tec_data)
        mean, std = scaler.mean_, scaler.scale_
        return std[0], mean[0]

    #read data from csv
    def get_data(self):
        dataset = []
        for file_name in os.listdir(self.path):
            list_col = np.arange(5123)
            data = pd.read_csv(os.path.join(self.path, file_name), skiprows= 5, usecols = list_col)
            data = data.values
            dataset.append(data[:, 11:])
        
        tec_data = dataset[0]
        for i in range(1, len(dataset)):
            tec_data = np.vstack((tec_data,dataset[i]))
        return tec_data

    #Create a dataset that fits the model
    def create_dataset(self) :
        _input, target = [], []
        for idx in range(self.input_history-1, len(self.tec_data)):
            if idx + self.window_size>= len(self.tec_data):
                break
            world_history = []
            if _input:
                world_history = _input[-1][1:]
                world_history.append(self.create_input(idx))
            else:
                for i in range(self.input_history):
                    world_history.append(self.create_input(i))
            target_world = self.create_target(idx)
            _input.append(world_history)
            target.append(target_world)
        return np.array(_input), np.array(target)

    def create_input(self, idx):
        world = []
        for longitude in range(71):
            latitude = []
            for lat in range(72):
                latitude.append(self.tec_data[idx][longitude*72 + lat])
            world.append(latitude)
        world.append([0 for _ in range(72)])
        return world

    def create_target(self, idx):
        #[9, 576]
        patch_count = 72*72//(self.patch_size*self.patch_size)
        target_world = [[]for _ in range(patch_count)]
        
        for longitude in range(71):
            for lat in range(72):
                patch_idx = (longitude//self.patch_size)*(72//self.patch_size) + lat//self.patch_size
                target_world[patch_idx].append(self.tec_data[idx + self.window_size][longitude*72 + lat])
        
        # padding zero to the last latitude
        for patch_idx in range(patch_count - (72//self.patch_size), patch_count): #padding zero to the final latitude
            for _ in range(self.patch_size): 
                target_world[patch_idx].append(0)
        # print(np.array(target_world).shape[:])
        return target_world

    def __len__(self):
        return len(self.target)

    def __getitem__(self, idx):
        _input = torch.tensor(self._input[idx], dtype=torch.float)
        target = torch.tensor(self.target[idx], dtype=torch.float)
        return _input, target,


if __name__ == '__main__':
    dataset = TECDataset('../data/valid', mode = 'None', window_size = 24, input_history = 6)
    dataloader = DataLoader(dataset, batch_size=24)
    for data in dataloader:
        print(np.shape(data[0]))
        print(np.shape(data[1]))
        print(data)
        input()
        break