import tensorflow as tf
from lib.util.ops import *
from lib.util.globals import *
from lib.util.hc_tf import *

def discriminator(config, x, g, xs, gs):
    layers = config['discriminator.densenet.layers']
    transitions = config['discriminator.densenet.transitions']
    k = config['discriminator.densenet.k']
    activation = config['discriminator.activation']
    batch_size = int(x.get_shape()[0])
    depth_increase = config['discriminator.pyramid.depth_increase']
    depth = config['discriminator.pyramid.layers']

    result = x
    result = conv2d(result, 16, name='d_expand', k_w=3, k_h=3, d_h=1, d_w=1)
    xgs = []
    for i in range(transitions):
      if(i!=0):
        xg = tf.concat(0, [xs[i], gs[i]])
        xg += tf.random_normal(xg.get_shape(), mean=0, stddev=config['d_noise'], dtype=config['dtype'])
        xgs.append(xg)
        result = tf.concat(3, [result, xg])

      for j in range(layers):
        result = dense_block(result, k, activation, batch_size, 'layer', 'd_layers_'+str(i)+"_"+str(j))
        print("densenet size", result)
      result = dense_block(result, k, activation, batch_size, 'transition', 'd_layers_transition_'+str(i))


    set_tensor("xgs", xgs)

    result = batch_norm(config['batch_size'], name='d_expand_bn_end_'+str(i))(result)
    result = activation(result)

    filter_size_w = 4
    filter_size_h = 4
    filter = [1,filter_size_w,filter_size_h,1]
    stride = [1,filter_size_w,filter_size_h,1]
    result = tf.nn.avg_pool(result, ksize=filter, strides=stride, padding='SAME')
    result = tf.reshape(result, [batch_size, -1])

    return result



