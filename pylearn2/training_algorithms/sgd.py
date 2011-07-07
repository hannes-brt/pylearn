import numpy as N
from theano import function
import theano.tensor as T
from warnings import warn

class SGD(object):
    """Stochastic Gradient Descent with an optional validation set for error monitoring

        TODO: right now, assumes there is just one variable, X, i.e. is designed for unsupervised learning
              need to support other tasks
    """

    def __init__(self,
            learning_rate,
            cost,
            batch_size = None ,
            batches_per_iter = 1000 ,
            monitoring_batches = - 1,
            monitoring_dataset = None):
        """
        TODO: for now, learning_rate is just a float, but later it should support passing in a class that dynamically adjusts
            the learning rate
        if batch_size is None, reverts to the force_batch_size field of the model
        if monitoring_dataset is provided, uses monitoring_batches batches of data from monitoring_dataset to report monitoring errors
        """

        #Store parameters
        self.learning_rate, self.batch_size, self.batches_per_iter = learning_rate, batch_size, batches_per_iter

        self.cost = cost

        if monitoring_dataset is None:
            assert monitoring_batches == -1
        self.monitoring_dataset, self.monitoring_batches = monitoring_dataset, monitoring_batches

        self.bSetup = False
        self.first = True
    #

    def setup(self, model):
        """ Should be called once before calls to train """

        self.model = model

        X = T.matrix(name='sgd_X')
        J = self.cost(model,X)
        if J.name is None:
            J.name = 'sgd_cost('+X.name+')'
        #

        params = model.get_params()

        for i, param in enumerate(params):
            if param.name is None:
                param.name = 'sgd_params[%d]' % i
            #
        #

        grads = dict(zip(params,T.grad(J, params)))

        for param in grads:
            if grads[param].name is None:
                grads[param].name = 'T.grad(' + J.name + ',' + param.name

        updates = dict(zip(params, [ param - self.learning_rate * grads[param]
                                    for param in params ] ) )

        for param in updates:
            if updates[param].name is None:
                updates[param].name = 'sgd_update('+param.name+')'
            #
        #

        model.censor_updates(updates)

        for param in updates:
            if updates[param] is None:
                updates[param].name = 'censor(sgd_update('+param.name+'))'
            #
        #

        self.sgd_update = function([X], updates = updates,name = 'sgd_update')

        self.params = params

        self.bSetup = True


        #TODO: currently just supports doing a gradient step on J(X)
        #      needs to support "side effects", e.g. updating persistent chains for SML
        #       (if we decide to implement SML as SGD)
    #


    def train(self, dataset):
        model = self.model

        if not self.bSetup:
            raise Exception("SGD.train called without first calling SGD.setup")

        if self.batch_size is None:
            batch_size = model.force_batch_size
        else:
            batch_size = self.batch_size
            if hasattr(model,"force_batch_size"):
                assert model.force_batch_size <= 0 or batch_size == model.force_batch_size
            #
        #

        for param in self.params:
            value = param.get_value(borrow=True)

            if N.any(N.isnan(value)) or N.any(N.isinf(value)):
                raise Exception("NaN in "+param.name)
            #
        #

        if self.first and self.monitoring_dataset:
            self.monitor()
        #

        self.first = False

        for i in xrange(self.batches_per_iter):
            X = dataset.get_batch_design(batch_size)

            #print '\n----------------'
            self.sgd_update(X)
            #print '----------------\n'

            #comment out this check when not debugging
            """for param in self.params:
                value = param.get_value(borrow=True)
                if N.any(N.isnan(value)):
                    raise Exception("NaN in "+param.name)
                #
            #"""

            model.batches_seen += 1
            model.examples_seen += batch_size
        #

        if self.monitoring_dataset:
            self.monitor()
        #

        return True
    #

    def monitor(self):
        model = self.model

        if True:
            s = self.monitoring_dataset.get_stream_position()

            self.monitoring_dataset.restart_stream()

            try:
                model.record_monitoring_error(self.monitoring_dataset,batches=self.monitoring_batches,batch_size=self.batch_size)
                print model.error_record[-1]
            except:
                warn( """Your model doesn't seem to support monitoring.
                         (TODO: implementing monitoring as part of training algorithm so
                         not all models have to do it. Actually implementation could probably even be
                         shared between multiple training algorithms """)
                self.monitoring_dataset = None
                return


            self.monitoring_dataset.set_stream_position(s)
        #
    #
#