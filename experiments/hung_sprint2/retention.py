"""Fixed source representation scales and latent/parameter retention losses."""

from __future__ import annotations

from copy import deepcopy
from typing import Iterable

import torch
from torch import Tensor

from experiments.hung_sprint2.model import ForecastGRU


def frozen_source_reference(source: ForecastGRU) -> ForecastGRU:
    """Clone source weights so target updates cannot mutate the reference."""
    reference = deepcopy(source).eval()
    reference.requires_grad_(False)
    return reference


@torch.no_grad()
def source_latent_scale(source: ForecastGRU, source_histories: Iterable[Tensor]) -> Tensor:
    """Population SD per latent dimension over *source-training* examples only.

    The caller supplies source-role permitted histories. This function cannot
    infer a role or cutoff from tensors, so that provenance must be recorded
    by the training job using the accepted input manifest.
    """
    was_training = source.training
    source.eval()
    try:
        latents = [source.encode(batch).detach() for batch in source_histories]
        if not latents or sum(batch.shape[0] for batch in latents) < 2:
            raise ValueError("At least two source-training examples are required")
        scale = torch.cat(latents, dim=0).std(dim=0, correction=0)
        validate_latent_scale(scale)
        return scale
    finally:
        source.train(was_training)


def validate_latent_scale(scale: Tensor) -> None:
    if scale.shape != (64,) or not scale.is_floating_point():
        raise ValueError("Source latent scale must be a floating tensor of shape [64]")
    if not torch.isfinite(scale).all() or torch.any(scale < 0):
        raise ValueError("Source latent scale must be finite and nonnegative")


def retention_loss(
    target_latent: Tensor, source_latent: Tensor, scale: Tensor, *, epsilon: float
) -> Tensor:
    """Mean over samples of 1/64 sum[((zT-zS)/(s+epsilon))²]."""
    if not (epsilon > 0 and epsilon < float("inf")):
        raise ValueError("epsilon must be finite and positive")
    validate_latent_scale(scale)
    if target_latent.ndim != 2 or target_latent.shape[1] != 64 or target_latent.shape[0] == 0:
        raise ValueError("Target latent must have shape [nonempty B,64]")
    if source_latent.shape != target_latent.shape:
        raise ValueError("Target/source latent shapes differ")
    if not torch.isfinite(target_latent).all() or not torch.isfinite(source_latent).all():
        raise ValueError("Latents must be finite")
    denominator = scale.to(dtype=target_latent.dtype, device=target_latent.device)
    denominator = denominator + target_latent.new_tensor(epsilon)
    if not torch.isfinite(denominator).all() or torch.any(denominator <= 0):
        raise ValueError("Retention denominator is not finite and positive in latent dtype")
    loss = (((target_latent - source_latent.detach()) / denominator) ** 2).mean()
    if not torch.isfinite(loss):
        raise ValueError("Retention loss is not finite")
    return loss


def parameter_retention_loss(target: ForecastGRU, source: ForecastGRU) -> Tensor:
    """Mean squared displacement of all transferred GRU/head parameters from Source."""
    target_parameters = dict(target.named_parameters())
    source_parameters = dict(source.named_parameters())
    if target_parameters.keys() != source_parameters.keys() or not target_parameters:
        raise ValueError("Parameter-retention source/target architecture differs")
    total: Tensor | None = None
    count = 0
    for name, parameter in target_parameters.items():
        anchor = source_parameters[name]
        if parameter.shape != anchor.shape or parameter.device != anchor.device:
            raise ValueError("Parameter-retention source/target parameter differs")
        if not torch.isfinite(parameter).all() or not torch.isfinite(anchor).all():
            raise ValueError("Parameter-retention weights must be finite")
        term = (parameter - anchor.detach()).square().sum()
        total = term if total is None else total + term
        count += parameter.numel()
    loss = total / count
    if not torch.isfinite(loss):
        raise ValueError("Parameter-retention loss is not finite")
    return loss
