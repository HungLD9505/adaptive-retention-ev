"""One-step validation hypergradient through the current Adam state."""

import math
from collections.abc import Callable

import torch
from torch import Tensor, nn
from torch.func import functional_call


def virtual_adam_step(
    model: nn.Module, optimizer: torch.optim.Adam, training_loss: Tensor
) -> dict[str, Tensor]:
    """Return differentiable virtual parameters without changing real Adam/model state.

    Matches standard torch Adam's coupled weight decay, bias correction and AMSGrad.
    The study rejects optimizer variants not used by the primary runner.
    """
    if not isinstance(optimizer, torch.optim.Adam):
        raise TypeError("The virtual step requires torch.optim.Adam")
    named = dict(model.named_parameters())
    parameters = list(named.values())
    gradients = torch.autograd.grad(training_loss, parameters, create_graph=True)
    by_id = {
        id(parameter): (name, gradient)
        for (name, parameter), gradient in zip(named.items(), gradients, strict=True)
    }
    updated = {}
    for group in optimizer.param_groups:
        if (
            group["capturable"]
            or group["differentiable"]
            or group["fused"]
            or group["foreach"]
            or group.get("decoupled_weight_decay", False)
        ):
            raise ValueError("Unsupported Adam execution variant")
        beta1, beta2 = group["betas"]
        lr, eps, decay = group["lr"], group["eps"], group["weight_decay"]
        if not all(math.isfinite(float(x)) for x in (beta1, beta2, lr, eps, decay)):
            raise ValueError("Nonfinite Adam setting")
        for parameter in group["params"]:
            name, gradient = by_id[id(parameter)]
            state = optimizer.state.get(parameter, {})
            step = int(state["step"].item()) + 1 if state else 1
            grad = -gradient if group["maximize"] else gradient
            if decay:
                grad = grad + decay * parameter
            previous_m = state["exp_avg"].detach() if state else torch.zeros_like(parameter)
            previous_v = state["exp_avg_sq"].detach() if state else torch.zeros_like(parameter)
            moment = beta1 * previous_m + (1 - beta1) * grad
            variance = beta2 * previous_v + (1 - beta2) * grad.square()
            if group["amsgrad"]:
                previous_max = (
                    state["max_exp_avg_sq"].detach() if state else torch.zeros_like(parameter)
                )
                variance = torch.maximum(previous_max, variance)
            # At an exact zero second moment, autograd's sqrt derivative is NaN.
            # The Adam quotient has a finite limiting derivative due to eps.
            # Clamping only subnormal variance preserves the forward step in
            # practical precision while exposing that limiting derivative.
            corrected_variance = variance / (1 - beta2**step)
            denominator = (
                corrected_variance.clamp_min(torch.finfo(parameter.dtype).tiny).sqrt() + eps
            )
            updated[name] = parameter - lr * (moment / (1 - beta1**step)) / denominator
    if set(updated) != set(named):
        raise ValueError("Adam parameter groups do not cover model exactly")
    if any(not torch.isfinite(value).all() for value in updated.values()):
        raise ValueError("Nonfinite virtual Adam parameter")
    return updated


def validation_hypergradient(
    model: nn.Module,
    optimizer: torch.optim.Adam,
    coefficient: Tensor,
    training_objective: Callable[[nn.Module, Tensor], Tensor],
    validation_objective: Callable[[dict[str, Tensor]], Tensor],
) -> tuple[Tensor, Tensor]:
    """Differentiate validation forecast loss through one exact virtual Adam step."""
    if coefficient.ndim != 0 or not coefficient.requires_grad or not torch.isfinite(coefficient):
        raise ValueError("Lambda must be a finite scalar requiring gradients")
    virtual = virtual_adam_step(model, optimizer, training_objective(model, coefficient))
    validation = validation_objective(virtual)
    if validation.ndim != 0 or not torch.isfinite(validation):
        raise ValueError("Nonfinite scalar validation objective")
    gradient = torch.autograd.grad(validation, coefficient)[0]
    if not torch.isfinite(gradient):
        raise ValueError("Nonfinite validation hypergradient")
    return gradient.detach(), validation.detach()


def forecast_with_virtual(
    model: nn.Module, parameters: dict[str, Tensor], *inputs: Tensor
) -> Tensor:
    """Evaluate a GRU or toy module at virtual weights without modifying it."""
    return functional_call(model, parameters, inputs)
