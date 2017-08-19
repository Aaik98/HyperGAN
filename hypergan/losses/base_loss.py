from hypergan.gan_component import GANComponent
import numpy as np
import tensorflow as tf

class BaseLoss(GANComponent):
    def __init__(self, gan, config, discriminator=None, generator=None):
        GANComponent.__init__(self, gan, config)
        self.metrics = {}
        self.sample = None
        self.ops = None
        if discriminator == None:
            discriminator = gan.discriminator
        if generator == None:
            generator = gan.generator
        self.discriminator = discriminator
        self.generator = generator

    def reuse(self, d_real, d_fake):
        self.discriminator.ops.reuse()
        net = self._create(d_real, d_fake)
        self.discriminator.ops.stop_reuse()
        return net


    def create(self, split=2):
        gan = self.gan
        config = self.config
        ops = self.gan.ops

        if self.discriminator is None:
            net = gan.discriminator.sample
        else:
            net = self.discriminator.sample

        if split == 2:
            d_real, d_fake = self.split_batch(net, split)
            d_loss, g_loss = self._create(d_real, d_fake)
        elif split == 3:
            d_real, d_fake, d_fake2 = self.split_batch(net, split)
            d_loss, g_loss = self._create(d_real, d_fake)
            d_loss2, g_loss2 = self.reuse(d_real, d_fake2)
            g_loss += g_loss2
            d_loss += d_loss2
            #does this double the signal of d_real?

        elif split == 5:
            d_real, d_fake, d_fake2, d_fake3, d_fake4 = self.split_batch(net, split)
            d_loss, g_loss = self._create(d_real, d_fake)
            d_loss2, g_loss2 = self.reuse(d_real, d_fake2)
            d_loss3, g_loss3 = self.reuse(d_real, d_fake3)
            d_loss4, g_loss4 = self.reuse(d_real, d_fake4)
            d_loss = tf.add_n([d_loss, d_loss2, d_loss3, d_loss4])
            g_loss = tf.add_n([g_loss, g_loss2, g_loss3, g_loss4])
            #does this double the signal of d_real?


        if d_loss is not None:
            d_loss = ops.squash(d_loss, tf.reduce_mean) #linear doesn't work with this, so we cant pass config.reduce
            self.metrics['d_loss'] = d_loss

            if config.minibatch:
                d_loss += self.minibatch(net)

            if config.gradient_penalty:
                gp = self.gradient_penalty()
                self.metrics['gradient_penalty'] = gp
                print("Gradient penalty applied")
                d_loss += gp

        if g_loss is not None:
            g_loss = ops.squash(g_loss, tf.reduce_mean)
            self.metrics['g_loss'] = g_loss

        self.metrics = self.metrics or sample_metrics

        self.sample = [d_loss, g_loss]
        self.d_loss = d_loss
        self.g_loss = g_loss

        return self.sample

    # This is openai's implementation of minibatch regularization
    def minibatch(self, net):
        discriminator = self.discriminator or self.gan.discriminator
        ops = discriminator.ops
        config = self.config
        batch_size = ops.shape(net)[0]
        single_batch_size = batch_size//2
        n_kernels = config.minibatch_kernels or 300
        dim_per_kernel = config.dim_per_kernel or 50
        print("[discriminator] minibatch from", net, "to", n_kernels*dim_per_kernel)
        x = ops.linear(net, n_kernels * dim_per_kernel)
        activation = tf.reshape(x, (batch_size, n_kernels, dim_per_kernel))

        big = np.zeros((batch_size, batch_size))
        big += np.eye(batch_size)
        big = tf.expand_dims(big, 1)
        big = tf.cast(big,dtype=ops.dtype)

        abs_dif = tf.reduce_sum(tf.abs(tf.expand_dims(activation,3) - tf.expand_dims(tf.transpose(activation, [1, 2, 0]), 0)), 2)
        mask = 1. - big
        masked = tf.exp(-abs_dif) * mask
        def half(tens, second):
            m, n, _ = tens.get_shape()
            m = int(m)
            n = int(n)
            return tf.slice(tens, [0, 0, second * single_batch_size], [m, n, single_batch_size])

        f1 = tf.reduce_sum(half(masked, 0), 2) / tf.reduce_sum(half(mask, 0))
        f2 = tf.reduce_sum(half(masked, 1), 2) / tf.reduce_sum(half(mask, 1))

        return ops.squash(ops.concat([f1, f2]))

    def gradient_penalty(self):
        config = self.config
        gan = self.gan
        ops = self.gan.ops
        gradient_penalty = config.gradient_penalty
        x = gan.inputs.x
        generator = self.generator or gan.generator
        g = generator.sample
        discriminator = self.discriminator or gan.discriminator
        shape = [1 for t in g.get_shape()]
        shape[0] = gan.batch_size()
        uniform_noise = tf.random_uniform(shape=shape,minval=0.,maxval=1.)
        print("[gradient penalty] applying x:", x, "g:", g, "noise:", uniform_noise)
        if config.gradient_penalty_type == 'dragan':
            axes = [0, 1, 2, 3]
            if len(ops.shape(x)) == 2:
                axes = [0, 1]
            mean, variance = tf.nn.moments(x, axes=axes)
            interpolates = x + uniform_noise * 0.5 * variance * tf.random_uniform(shape=ops.shape(x), minval=0.,maxval=1.)
        else:
            interpolates = x + uniform_noise * (g - x)
        reused_d = discriminator.reuse(interpolates)
        gradients = tf.gradients(reused_d, [interpolates])[0]
        penalty = tf.sqrt(tf.reduce_sum(tf.square(gradients), axis=1))
        penalty = tf.reduce_mean(tf.square(penalty - 1.))
        return float(gradient_penalty) * penalty

    def sigmoid_kl_with_logits(self, logits, targets):
       # broadcasts the same target value across the whole batch
       # this is implemented so awkwardly because tensorflow lacks an x log x op
       assert isinstance(targets, float)
       if targets in [0., 1.]:
         entropy = 0.
       else:
         entropy = - targets * np.log(targets) - (1. - targets) * np.log(1. - targets)
         return tf.nn.sigmoid_cross_entropy_with_logits(logits=logits, labels=tf.ones_like(logits) * targets) - entropy
