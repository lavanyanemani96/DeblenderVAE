# Import necessary librairies
import numpy as np
import matplotlib.pyplot as plt
import sys
import os
import logging
import galsim
import random
import cmath as cm
import math
from tensorflow.keras import backend as K
from tensorflow.keras import metrics
from tensorflow.keras.models import Model, Sequential
from scipy.stats import norm
from tensorflow.keras import backend as K
from tensorflow.keras import metrics
from tensorflow.keras.layers import Conv2D, Input, Dense, Dropout, MaxPool2D, Flatten,  Reshape, UpSampling2D, Cropping2D, Conv2DTranspose, PReLU, Concatenate, Lambda, BatchNormalization, concatenate
from tensorflow.keras.models import Model, Sequential
from tensorflow.keras import metrics
from tensorflow.keras.callbacks import Callback, ReduceLROnPlateau, TerminateOnNaN, ModelCheckpoint
import tensorflow as tf
import tensorflow_probability as tfp

from generator_vae import BatchGenerator_lsst_r_band
import vae_functions, model
from utils import load_vae_conv
from callbacks import changeAlpha

######## Import data for callback (Only if VAEHistory is used)
# x = np.load('/sps/lsst/users/barcelin/data/single/galaxies_COSMOS_5_v5_test.npy')
# x_val = x[:500,1,6].reshape((500,64,64,1))
# # Normalize the data for callback
# I= [6.48221069e+05, 4.36202878e+05, 2.27700000e+05, 4.66676013e+04,2.91513800e+02, 2.64974100e+03, 4.66828170e+03, 5.79938030e+03,5.72952590e+03, 3.50687710e+03]
# beta = 1
# for i in range (500):
#     x_val[i] = np.tanh(np.arcsinh(x_val[i]/(I[6]/beta)))

######## Set some parameters
batch_size = 100
original_dim = 64*64*1
latent_dim = 64
intermediate_dim = 2000
epochs = 1000
epsilon_std = 1.0

######## Load VAE
encoder, decoder = model.vae_model(1)

######## Build the VAE
vae, vae_utils, output_encoder = vae_functions.build_vanilla_vae(encoder, decoder, full_cov=False, coeff_KL = 0)

######## Define the loss function
alpha = K.variable(0.0001)

def vae_loss(x, x_decoded_mean):
     xent_loss = original_dim*K.mean(K.sum(K.binary_crossentropy(x, x_decoded_mean), axis=[1,2,3]))
     kl_loss = - .5 * K.get_value(alpha) * K.sum(1 + output_encoder[1] - K.square(output_encoder[0]) - K.exp(output_encoder[1]), axis=-1)
     return xent_loss + K.mean(kl_loss)

######## Compile the VAE
vae.compile('adam', loss=vae_loss, metrics=['mse'])

######## Fix the maximum learning rate in adam
K.set_value(vae.optimizer.lr, 0.0001)

#######
# Callback
#alphaChanger = changeAlpha(alpha, vae, epochs)
# Callback to display evolution of training
# # vae_hist = vae_functions.VAEHistory(x_val[:500], vae_utils, latent_dim, alpha, plot_bands=0, figname='/sps/lsst/users/barcelin/callbacks/R_band/VAE/noisy/v5/test_noisy_v4')#noisy_
# Keras Callbacks
earlystop = tf.keras.callbacks.EarlyStopping(monitor='val_mean_squared_error', min_delta=0.0000001, patience=10, verbose=0, mode='min', baseline=None)
checkpointer_mse = tf.keras.callbacks.ModelCheckpoint(filepath='/sps/lsst/users/barcelin/weights/R_band/VAE/noisy/v9_64ld/mse/weights.{epoch:02d}-{val_mean_squared_error:.2f}.ckpt', monitor='val_mean_squared_error', verbose=1, save_best_only=True,save_weights_only=True, mode='min', period=1)
checkpointer_loss = tf.keras.callbacks.ModelCheckpoint(filepath='/sps/lsst/users/barcelin/weights/R_band/VAE/noisy/v9_64ld/loss/weights.{epoch:02d}-{val_loss:.2f}.ckpt', monitor='val_loss', verbose=1, save_best_only=True,save_weights_only=True, mode='min', period=1)
tbCallBack = tf.keras.callbacks.TensorBoard(log_dir='/sps/lsst/users/barcelin/Graph/vae_lsst_r_band/noisy/v6', histogram_freq=0, batch_size = batch_size, write_graph=True, write_images=True)

######## Define all used callbacks
callbacks = [checkpointer_loss, checkpointer_mse]#, tbCallBack]#, alphaChanger earlystop,vae_hist, checkpointer, vae_hist, 
 
######## List of data samples
list_of_samples=['/sps/lsst/users/barcelin/data/single/galaxies_COSMOS_1_v5_test.npy',
                 '/sps/lsst/users/barcelin/data/single/galaxies_COSMOS_2_v5_test.npy',
                 '/sps/lsst/users/barcelin/data/single/galaxies_COSMOS_3_v5_test.npy',
                 '/sps/lsst/users/barcelin/data/single/galaxies_COSMOS_4_v5_test.npy',
                 '/sps/lsst/users/barcelin/data/single/galaxies_COSMOS_5_v5_test.npy',
                ]

######## Define the generators
training_generator = BatchGenerator_lsst_r_band(list_of_samples,total_sample_size=180000, batch_size= batch_size, training_or_validation = 'training', noisy = True)#180000
validation_generator = BatchGenerator_lsst_r_band(list_of_samples,total_sample_size=20000, batch_size= batch_size, training_or_validation = 'validation', noisy = True)#20000

######## Train the network
hist = vae.fit_generator(generator=training_generator, epochs=epochs,#_noisy
                  steps_per_epoch=1800,#1800
                  verbose=2,
                  shuffle = True,#int(ntrain/batch_size),
                  validation_data=validation_generator,
                  validation_steps=200,#200
                  callbacks=callbacks,
                  workers = 0)

# Save the weights of last epoch
#vae.save_weights("/pbs/throng/lsst/users/barcelin/R_BAND_test/v6/vae_conv_lsst_R_band_callbacks_NOISY_TEST")