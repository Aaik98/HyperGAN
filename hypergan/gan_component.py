import hyperchamber as hc
import inspect


class ValidationException(Exception):
    pass

class GANComponent:
    def __init__(self, gan, config):
        self.config = hc.Config(config)
        self.gan = gan
        errors = self.validate()
        if errors != []:
            raise ValidationException("\n".join(errors))
        self.ops = self.create_ops()

    def create_ops(self):
        if self.gan is None:
            return None
        filtered_options = {k: v for k, v in self.config.items() if k in inspect.getargspec(self.gan.ops_backend).args}
        print('create_ops', self.gan, self.gan.ops_backend)
        print("filtered_options", filtered_options)
        ops = self.gan.ops_backend(*dict(filtered_options))
        return ops

    def required(self):
        return []

    def validate(self):
        errors = []
        required = self.required()
        for argument in required:
            if(self.config.__getattr__(argument) == None):
                errors.append("`"+argument+"` required")

        if(self.gan is None):
            errors.append("GANComponent constructed without GAN")
        return errors

    def weights(self):
        return self.ops.weights

    def biases(self):
        return self.ops.biases

    def variables(self):
        return self.ops.variables()

