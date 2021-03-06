import tensorflow as tf
import numpy as np
from utils.utils import *
import sys
import os
import math
import time
from glob import glob
from random import shuffle
from utils.download import download_celeb_a, download_lsun
from utils.Lsun import Lsun

def one_hot_encoded(x):    
    output = np.zeros([np.size(x),10])
    for i, index in enumerate(x):
        output[i,index]=1
    return output

def data_loader(dataset):
    if dataset == 'mnist':
        mb_size = 256
        X_dim = 784
        width = 28
        height = 28
        channels = 1
        len_x_train = 60000
        len_x_test = 10000
        (x_train, y_train), (x_test, y_test) = tf.keras.datasets.mnist.load_data()

        x_train = normalize(x_train)
        x_test = normalize(x_test)
        y_train = one_hot_encoded(y_train)
        y_test = one_hot_encoded(y_test)
        x_train = np.reshape(x_train,[-1,28,28,1])
        x_test = np.reshape(x_test,[-1,28,28,1])
        
    if dataset == 'fmnist':
        mb_size = 256
        X_dim = 784
        width = 28
        height = 28
        channels = 1
        len_x_train = 60000
        len_x_test = 10000
        (x_train, y_train), (x_test, y_test) = tf.keras.datasets.fashion_mnist.load_data()

        x_train = normalize(x_train)
        x_test = normalize(x_test)
        y_train = one_hot_encoded(y_train)
        y_test = one_hot_encoded(y_test)
        x_train = np.reshape(x_train,[-1,28,28,1])
        x_test = np.reshape(x_test,[-1,28,28,1])
        
    if dataset == 'svhn':
        mb_size = 256
        X_dim = 1024
        width = 32
        height = 32
        channels = 3    
        len_x_train = 73257
        len_x_test = 26032

        train_location = 'data/SVHN/train_32x32.mat'
        test_location = 'data/SVHN/test_32x32.mat'

        train_dict = sio.loadmat(train_location)
        Y_train = train_dict['y']
        for i in range(len(Y_train)):
            if Y_train[i]%10 == 0:
                Y_train[i] = 0
        x_ = np.asarray(train_dict['X'])
        y_ = np.asarray(train_dict['y'])

        x_train = []
        for i in range(x_.shape[3]):
            x_train.append(x_[:,:,:,i])
        x_train = np.asarray(x_train)
        x_train = normalize(x_train)
        y_train = one_hot_encoded(y_)
        
        test_dict = sio.loadmat(test_location)
        Y_test = test_dict['y']
        for i in range(len(Y_test)):
            if Y_test[i]%10 == 0:
                Y_test[i] = 0
                
        x_ = np.asarray(test_dict['X'])
        y_ = np.asarray(Y_test)

        x_test = []
        for i in range(x_.shape[3]):
            x_test.append(x_[:,:,:,i])
        x_test = np.asarray(x_test)
        x_test = normalize(x_test)
        y_test = one_hot_encoded(y_)

    if dataset == 'cifar10':
        mb_size = 256
        X_dim = 1024
        len_x_train = 50000
        len_x_test = 10000
        width = 32
        height = 32
        channels = 3    
        (x_train, y_train), (x_test, y_test) = tf.keras.datasets.cifar10.load_data()
        x_train = normalize(x_train)
        x_test = normalize(x_test)
        y_train = one_hot_encoded(y_train)
        y_test = one_hot_encoded(y_test)
        
    return mb_size, X_dim, width, height, channels,len_x_train, x_train, y_train, len_x_test, x_test, y_test 