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

sys.path.insert(0,'../tools_for_VAE/')
from tools_for_VAE import vae_functions, model, utils, callbacks, generator
from tools_for_VAE.callbacks import changeAlpha


######## Set some parameters
batch_size = 100
latent_dim = 32
epochs = 2000
bands = [6]

######## Import data for callback (Only if VAEHistory is used)
x_val= np.load('/sps/lsst/users/barcelin/data/single_galaxies/28/validation/galaxies_isolated_20191022_0_images.npy', mmap_mode = 'c')[:500,:,bands].transpose([0,1,3,4,2])
#x_val = utils.norm(np.expand_dims(x[:500,1,6], axis = 1), bands).transpose([0,2,3,1])

path_output = '/sps/lsst/users/barcelin/weights/R_band/VAE/noisy/v29/mse/'#v21/bis_bis/mse/  #v28


######## Load encoder, decoder
encoder, decoder = model.vae_model(latent_dim, len(bands))

######## Build the VAE
vae, vae_utils,  Dkl = vae_functions.build_vanilla_vae(encoder, decoder, full_cov=False, coeff_KL = 0)

############## Comment or not depending on what's necessary
# Load weights
vae, vae_utils, encoder, Dkl = utils.load_vae_conv(path_output, len(bands), folder = True)#, output_encoder
#K.set_value(alpha, utils.load_alpha('/sps/lsst/users/barcelin/weights/R_band/VAE/noisy/v_test3/'))

print(vae.summary())

######## Define the loss function
alpha = K.variable(10-2)

def vae_loss(x, x_decoded_mean):
     xent_loss = K.mean(K.sum(K.binary_crossentropy(x, x_decoded_mean), axis=[1,2,3]))
     kl_loss =  K.get_value(alpha) * Dkl
     return xent_loss + K.mean(kl_loss)

######## Compile the VAE
vae.compile('adam', loss=vae_loss, metrics=['mse'])

######## Fix the maximum learning rate in adam
K.set_value(vae.optimizer.lr, 0.001)

#######
# Callback
path_weights = '/sps/lsst/users/barcelin/weights/R_band/VAE/noisy/v29/'
path_plots = '/sps/lsst/users/barcelin/callbacks/R_band/VAE/noisy/v29/'
path_tb = '/sps/lsst/users/barcelin/Graph/vae_lsst_r_band/noisy/'

alphaChanger = callbacks.changeAlpha(alpha, vae, vae_loss, path_weights)
# Callback to display evolution of training
vae_hist = vae_functions.VAEHistory(x_val, vae_utils, latent_dim, alpha, plot_bands=[0], figroot=path_plots+'test_', period = 5)
# Keras Callbacks
#earlystop = tf.keras.callbacks.EarlyStopping(monitor='val_mean_squared_error', min_delta=0.0000001, patience=10, verbose=0, mode='min', baseline=None)
checkpointer_mse = tf.keras.callbacks.ModelCheckpoint(filepath=path_weights+'mse/weights.{epoch:02d}-{val_mean_squared_error:.2f}.ckpt', monitor='val_mean_squared_error', verbose=1, save_best_only=True,save_weights_only=True, mode='min', period=1)
checkpointer_loss = tf.keras.callbacks.ModelCheckpoint(filepath=path_weights+'loss/weights.{epoch:02d}-{val_loss:.2f}.ckpt', monitor='val_loss', verbose=1, save_best_only=True,save_weights_only=True, mode='min', period=1)
#tbCallBack = tf.keras.callbacks.TensorBoard(log_dir=path_tb+'v6', histogram_freq=0, batch_size = batch_size, write_graph=True, write_images=True)

######## Define all used callbacks
callbacks = [vae_hist, checkpointer_mse,checkpointer_loss]#,checkpointer_loss, tbCallBack]#, alphaChanger earlystop,vae_hist, checkpointer,  
 
######## List of data samples
images_dir = '/sps/lsst/users/barcelin/data/single_galaxies/28/'
list_of_samples = [x for x in utils.listdir_fullpath(os.path.join(images_dir,'training')) if x.endswith('.npy')]
list_of_samples_val = [x for x in utils.listdir_fullpath(os.path.join(images_dir,'validation')) if x.endswith('.npy')]

######## Define the generators
training_generator = generator.BatchGenerator(bands, list_of_samples,total_sample_size=None, 
                                             batch_size= batch_size, 
                                             trainval_or_test = 'training', 
                                             do_norm = False,
                                             denorm = False,
                                             list_of_weights_e = None)

validation_generator = generator.BatchGenerator(bands, list_of_samples_val,total_sample_size=None, 
                                             batch_size= batch_size, 
                                             trainval_or_test = 'validation', 
                                             do_norm = False,
                                             denorm = False,
                                             list_of_weights_e = None)

######## Train the network
hist = vae.fit_generator(generator=training_generator, epochs=epochs,
                  steps_per_epoch=32,#2800
                  verbose=1,
                  shuffle = True,
                  validation_data=validation_generator,
                  validation_steps=2,#400
                  callbacks=callbacks,
                  workers = 0)
