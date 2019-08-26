import tensorflow as tf
import numpy as np

INIT_EPSILON=1.0
INIT_DELTA = 1e-5
USE_DELTA = True

def xavier_init(size):
    in_dim = size[0]
    xavier_stddev = 1. / tf.sqrt(in_dim / 2.)
    return tf.random_normal(shape=size, stddev=xavier_stddev)

def he_normal_init(size):
    in_dim = size[0]
    he_stddev = tf.sqrt(2./in_dim)
    return tf.random_normal(shape=size, stddev=he_stddev)

def epsilon_init(initial, size):
    in_dim = size[0]
    stddev = 1. / tf.sqrt(in_dim / 2.)
    return tf.add(initial,tf.random_normal(shape=size, stddev=stddev))

def delta_init(initial, size):
    in_dim = size[0]
    stddev = 1. / tf.sqrt(in_dim / 2.)
    return tf.add(initial,tf.random_normal(shape=size, stddev=stddev))

def generator(input_shape, n_filters, filter_sizes, x, noise, var_G, var_A, sensitivity,
              reuse=False,use_delta=USE_DELTA):
    idx=0
    current_input = x    
    encoder = []
    var_P = []
    shapes_enc = []
    with tf.name_scope("Encoder"):
        for layer_i, n_output in enumerate(n_filters[1:]):
            n_input = current_input.get_shape().as_list()[3]
            shapes_enc.append(current_input.get_shape().as_list())
            if reuse:
                W = var_A[idx]
                var_P.append(W)
                idx += 1
            else:
                W = tf.Variable(xavier_init([filter_sizes[layer_i],
                                            filter_sizes[layer_i],
                                            n_input, n_output]))
                var_A.append(W)
                var_P.append(W)
            encoder.append(W)
            conv = tf.nn.conv2d(current_input, W, strides=[1, 2, 2, 1], padding='SAME')          
            conv = tf.contrib.layers.batch_norm(conv,
                                                updates_collections=None,
                                                decay=0.9,
                                                zero_debias_moving_mean=True,
                                                is_training=True)
            output = tf.nn.leaky_relu(conv)
            current_input = output
        encoder.reverse()
        shapes_enc.reverse() 
        z_flat = tf.layers.flatten(current_input)
        z_dim = int(z_flat.get_shape()[1])
        z = z_flat  

    #epsilon-delta-DP        
    if use_delta:
        with tf.name_scope("Noise_Applier"):       
            z_original = z
            if reuse == True:
                W_epsilon = var_A[idx]
                epsilon_var = W_epsilon
                idx += 1
            else:
                W_epsilon = tf.Variable(epsilon_init(INIT_EPSILON, [z_dim]))
                epsilon_var = W_epsilon
                var_G.append(W_epsilon)
                var_A.append(W_epsilon)
            W_epsilon = tf.maximum(tf.abs(W_epsilon),1e-8)
            if reuse == True:
                W_delta = var_A[idx]
                delta_var = W_delta
                idx += 1
            else:
                W_delta = tf.Variable(delta_init(INIT_DELTA, [z_dim]))
                delta_var = W_delta
                var_G.append(W_delta)
                var_A.append(W_delta)
            W_delta = tf.maximum(W_delta,1e-8)
            W_delta = tf.minimum(W_delta, 1.0)
            dp_delta = tf.log(tf.divide(1.25,W_delta))
            dp_delta = tf.maximum(dp_delta,0)
            dp_delta = tf.sqrt(tf.multiply(2.0,dp_delta))      
            dp_lambda = tf.multiply(dp_delta,tf.divide(sensitivity,W_epsilon))
            W_noise = tf.multiply(noise,dp_lambda)
            z = tf.add(z,W_noise)
            z_noise = W_noise
            z_noise_applied = z
        
    #epsilon-DP              
    else:
        with tf.name_scope("Noise_Applier"):      
            z_original = z
            if reuse == True:
                W_epsilon = var_A[idx]
                epsilon_var = W_epsilon
                idx += 1
            else:
                W_epsilon = tf.Variable(epsilon_init(INIT_EPSILON, [z_dim]))
                epsilon_var = W_epsilon
                var_G.append(W_epsilon)
                var_A.append(W_epsilon)
            W_epsilon = tf.maximum(W_epsilon,1e-8)
            dp_lambda = tf.divide(sensitivity,W_epsilon)
            W_noise = tf.multiply(noise,dp_lambda)
            z = tf.add(z,W_noise)
            z_noise = W_noise
            z_noise_applied = z
            
    with tf.name_scope("Decoder"):  
        current_input = tf.reshape(z, [-1, 4, 4, n_filters[-1]])           
        for layer_i, shape in enumerate(shapes_enc):
            W_enc = encoder[layer_i]
            if reuse == True:
                W = var_A[idx]
                var_P.append(W)
                idx += 1
            else:
                W = tf.Variable(he_normal_init(W_enc.get_shape().as_list()))
                var_G.append(W)
                var_A.append(W)
                var_P.append(W)
            deconv = tf.nn.conv2d_transpose(current_input, 
                                            W,
                                            tf.stack([tf.shape(x)[0], shape[1], shape[2], shape[3]]),
                                            strides=[1, 2, 2, 1], 
                                            padding='SAME') 
            
            if layer_i == len(n_filters)-2:
                output = tf.nn.sigmoid(deconv)
            else:
                deconv = tf.contrib.layers.batch_norm(deconv,
                                                      updates_collections=None,
                                                      decay=0.9,
                                                      zero_debias_moving_mean=True,
                                                      is_training=True)           
                output = tf.nn.leaky_relu(deconv)
            current_input = output
        g = current_input
  
    return g, z_original, z_noise, z_noise_applied, var_P

def discriminator(x,var_D):
    current_input = x
    with tf.name_scope("Discriminator"):
        for i in range(len(var_D)-2):
            conv = tf.nn.conv2d(current_input, var_D[i], strides=[1,2,2,1],padding='SAME')
            conv = tf.contrib.layers.layer_norm(conv)
            current_input = tf.nn.leaky_relu(conv)            
        h = tf.layers.flatten(current_input)     
        d = tf.nn.xw_plus_b(h, var_D[-2], var_D[-1])
        
    return d

def classifier(x, var_C):
    current_input = x
    with tf.name_scope("Discriminator"):
        for i in range(len(var_C)-2):
            conv = tf.nn.conv2d(current_input, var_C[i], strides=[1,2,2,1],padding='SAME')
            conv = tf.contrib.layers.layer_norm(conv)
            current_input = tf.nn.leaky_relu(conv)            
        h = tf.layers.flatten(current_input)     
        d = tf.nn.xw_plus_b(h, var_C[-2], var_C[-1])
    return d

def gradient_penalty(G_sample, A_true_flat, mb_size, var_D):
    epsilon = tf.random_uniform(shape=[mb_size, 1, 1, 1], minval=0.,maxval=1.)
    X_hat = A_true_flat + epsilon * (G_sample - A_true_flat)
    D_X_hat = discriminator(X_hat,var_D)
    grad_D_X_hat = tf.gradients(D_X_hat, [X_hat])[0]
    red_idx = list(range(1, X_hat.shape.ndims))
    slopes = tf.sqrt(tf.reduce_sum(tf.square(grad_D_X_hat), reduction_indices=red_idx))
    gradient_penalty = tf.reduce_mean(tf.square(slopes - 1.))
    return gradient_penalty


