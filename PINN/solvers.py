import torch
from abc import ABC, abstractmethod

class Approximator(ABC):
    r"""The base class of approximators. An approximator is an approximation of the differential equation's solution.
    It knows the parameters in the neural network, and how to calculate the loss function and the metrics.
    """
    @abstractmethod
    def __call__(self):
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    def parameters(self):
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    def calculate_loss(self):
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    def calculate_metrics(self):
        raise NotImplementedError  # pragma: no cover

class SingleNetworkApproximator2DSpatial(Approximator):
    r"""An approximator to approximate the solution of a 2D steady-state problem.
    The boundary condition will be enforced by a regularization term in the loss function.

    :param single_network: A neural network with 2 input nodes (x, y) and 1 output node.
    :type single_network: `torch.nn.Module`
    :param pde: The PDE to solve. If the PDE is :math:`F(u, x, y) = 0` then `pde`
        should be a function that maps :math:`(u, x, y)` to :math:`F(u, x, y)`.
    :type pde: function
    :param boundary_conditions: A list of boundary conditions.
    :type boundary_conditions: list[`temporal.BoundaryCondition`]
    :param boundary_strictness: The regularization parameter, defaults to 1.
        A larger regularization parameter enforces the boundary conditions more strictly.
    :type boundary_strictness: float
    """
    def __init__(self, single_network, pde, boundary_conditions, boundary_strictness=1.):
        self.single_network = single_network
        self.pde = pde
        self.boundary_conditions = boundary_conditions
        self.boundary_strictness = boundary_strictness

    def __call__(self, xx, yy):
        xx = torch.unsqueeze(xx, dim=1).requires_grad_()
        yy = torch.unsqueeze(yy, dim=1).requires_grad_()
        xy = torch.cat((xx, yy), dim=1)
        uu = self.single_network(xy)
        uu = uu.requires_grad_()  # Ensure that uu also requires gradients
        return torch.squeeze(uu)
    
    def parameters(self):
        return self.single_network.parameters()

    def calculate_loss(self, xx, yy):
        uu = self.__call__(xx, yy)

        equation_mse = torch.mean(self.pde(uu, xx, yy)**2)

        boundary_mse = self.boundary_strictness * sum(self._boundary_mse(bc) for bc in self.boundary_conditions)
        h1=0.02  #高
        #weight_pde=h1 ** 4 /3
        #weight_pde=0.2
        return equation_mse + boundary_mse

    def _boundary_mse(self, bc):
        xx, yy = next(bc.points_generator)
        uu= self.__call__(xx.requires_grad_(), yy.requires_grad_())
        return torch.mean(bc.form(uu, xx, yy) ** 2) *bc.weight

    def calculate_metrics(self, xx, yy, metrics):
        uu = self.__call__(xx, yy)

        return {
            metric_name: metric_func(uu, xx, yy)
            for metric_name, metric_func in metrics.items()
        }

def _train_2dspatial(train_generator_spatial, train_generator_temporal,
                     approximator, optimizer, metrics, shuffle, batch_size):
    xx, yy = next(train_generator_spatial)
    xx.requires_grad = True
    yy.requires_grad = True
    training_set_size = len(xx)
    idx = torch.randperm(training_set_size) if shuffle else torch.arange(training_set_size)

    batch_start, batch_end = 0, batch_size
    while batch_start < training_set_size:
        if batch_end > training_set_size:
            batch_end = training_set_size
        batch_idx = idx[batch_start:batch_end]
        batch_xx = xx[batch_idx]
        batch_yy = yy[batch_idx]

        batch_loss = approximator.calculate_loss(batch_xx, batch_yy)

        optimizer.zero_grad()
        batch_loss.backward()
        optimizer.step()

        batch_start += batch_size
        batch_end += batch_size

    epoch_loss = approximator.calculate_loss(xx, yy).item()

    epoch_metrics = approximator.calculate_metrics(xx, yy, metrics)
    for k, v in epoch_metrics.items():
        epoch_metrics[k] = v.item()

    return epoch_loss, epoch_metrics


# validation phase for 2D steady-state problems
def _valid_2dspatial(valid_generator_spatial, valid_generator_temporal, approximator, metrics):
    xx, yy = next(valid_generator_spatial)
    xx.requires_grad = True
    yy.requires_grad = True

    epoch_loss = approximator.calculate_loss(xx, yy).item()

    epoch_metrics = approximator.calculate_metrics(xx, yy, metrics)
    for k, v in epoch_metrics.items():
        epoch_metrics[k] = v.item()

    return epoch_loss, epoch_metrics

def _solve_2dspatial(
    train_generator_spatial, valid_generator_spatial,
    approximator, optimizer, batch_size, max_epochs, shuffle, metrics, monitor
):
    r"""Solve a 2D steady-state problem

    :param train_generator_spatial:
        A generator to generate 2D spatial points for training.
    :type train_generator_spatial: generator
    :param valid_generator_spatial:
        A generator to generate 2D spatial points for validation.
    :type valid_generator_spatial: generator
    :param approximator:
        An approximator for 2D time-state problem.
    :type approximator: `temporal.SingleNetworkApproximator2DSpatial`, `temporal.SingleNetworkApproximator2DSpatialSystem`, or a custom `temporal.Approximator`
    :param optimizer:
        The optimization method to use for training.
    :type optimizer: `torch.optim.Optimizer`
    :param batch_size:
        The size of the mini-batch to use.
    :type batch_size: int
    :param max_epochs:
        The maximum number of epochs to train.
    :type max_epochs: int
    :param shuffle:
        Whether to shuffle the training examples every epoch.
    :type shuffle: bool
    :param metrics:
        Metrics to keep track of during training.
        The metrics should be passed as a dictionary where the keys are the names of the metrics,
        and the values are the corresponding function.
        The input functions should be the same as `pde` (of the approximator) and the output should be a numeric value.
        The metrics are evaluated on both the training set and validation set.
    :type metrics: dict[string, callable]
    :param monitor:
        The monitor to check the status of nerual network during training.
    :type monitor: `temporal.Monitor2DSpatial` or `temporal.MonitorMinimal`
    """
    return _solve_spatial_temporal(
        train_generator_spatial, None, valid_generator_spatial, None,
        approximator, optimizer, batch_size, max_epochs, shuffle, metrics, monitor,
        train_routine=_train_2dspatial, valid_routine=_valid_2dspatial
    )


# _solve_1dspatial_temporal, _solve_2dspatial_temporal, _solve_2dspatial all call this function in the end
def _solve_spatial_temporal(
    train_generator_spatial, train_generator_temporal, valid_generator_spatial, valid_generator_temporal,
    approximator, optimizer, batch_size, max_epochs, shuffle, metrics, monitor,
    train_routine, valid_routine
):
    history = {'train_loss': [], 'valid_loss': []}
    for metric_name, _ in metrics.items():
        history['train_' + metric_name] = []
        history['valid_' + metric_name] = []

    for epoch in range(max_epochs):
        train_epoch_loss, train_epoch_metrics = train_routine(
            train_generator_spatial, train_generator_temporal, approximator, optimizer, metrics, shuffle, batch_size
        )
        history['train_loss'].append(train_epoch_loss)
        for metric_name, metric_value in train_epoch_metrics.items():
            history['train_' + metric_name].append(metric_value)

        valid_epoch_loss, valid_epoch_metrics = valid_routine(
            valid_generator_spatial, valid_generator_temporal, approximator, metrics
        )
        history['valid_loss'].append(valid_epoch_loss)
        for metric_name, metric_value in valid_epoch_metrics.items():
            history['valid_' + metric_name].append(metric_value)

        if monitor and epoch % monitor.check_every == 0:
            monitor.check(approximator, history)
        if epoch % 1000==0:
            print("Already calculate for "+ str(epoch) + "/"+str(max_epochs))

    return approximator, history