from hypergan.samplers.base_sampler import BaseSampler
from hypergan.samplers.batch_sampler import BatchSampler
from hypergan.samplers.static_batch_sampler import StaticBatchSampler
from hypergan.samplers.random_walk_sampler import RandomWalkSampler
from hypergan.samplers.segment_sampler import SegmentSampler
import tensorflow as tf
import numpy as np
import hypergan as hg
from hypergan.losses.boundary_equilibrium_loss import BoundaryEquilibriumLoss
from hypergan.generators.segment_generator import SegmentGenerator


class DebugSampler(BaseSampler):
    def __init__(self, gan, samples_per_row=8):
        BaseSampler.__init__(self, gan, samples_per_row)
        self.samplers = [
            StaticBatchSampler(gan, samples_per_row),
            BatchSampler(gan, samples_per_row),
            RandomWalkSampler(gan, samples_per_row)
        ]


        if isinstance(gan.generator, SegmentGenerator):
            self.samplers += [SegmentSampler(gan)]

    def _sample(self):
        samples = [sampler._sample()['generator'] for sampler in self.samplers]
        print('----', [np.shape(sample) for sample in samples])
        all_samples = np.vstack(samples)
        print("ALL_SAMPLES:", np.shape(all_samples))

        return {
            'generator':all_samples
        }

