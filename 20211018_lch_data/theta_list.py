#! /usr/bin/env python

import pickle
from matplotlib import pyplot as plt

with open('theta_data.pickle', 'rb') as th:
    theta_list = pickle.load(th)

count = len(theta_list)
print(count)

import pandas as pd

# Create pandas data frame
indexName = { "theta1":[], 
              "theta2":[], 
              "theta3":[], 
              "theta4":[] }
csv_pd = pd.DataFrame(columns = indexName)

for i in range(0, count):
    print(theta_list[i])

    csv_pd.loc[i] = theta_list[i]

# save data
csv_pd.to_csv('data.csv')




