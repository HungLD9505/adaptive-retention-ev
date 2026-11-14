"""Read-only loss and encoder-gradient measurements on an arrived training day."""

import torch

from ev_models.model import ForecastGRU, forecast_loss, retention_loss


def measure(
    model: ForecastGRU,
    reference: ForecastGRU,
    latent_scale: torch.Tensor,
    record: dict,
    weight: float,
    *,
    epsilon: float,
    device: str,
) -> dict:
    """Use autograd.grad without modifying parameter gradients or optimizer state."""
    x, c, y = (
        torch.tensor([record[key]], dtype=torch.float32, device=device)
        for key in ("x_hist", "c_future", "y_scaled")
    )
    previous = model.training
    try:
        model.train()
        with torch.no_grad():
            source = reference.encode(x)
        z = model.encode(x)
        forecast = forecast_loss(model(x, c), y)
        retention = retention_loss(z, source, latent_scale.to(device), epsilon)
        parameters = list(model.encoder.parameters())
        gf = torch.autograd.grad(forecast, parameters)
        gr = torch.autograd.grad(retention, parameters)
        a = torch.cat([value.flatten().double() for value in gf])
        b = torch.cat([value.flatten().double() for value in gr])
        nf, nr = a.norm().item(), b.norm().item()
        result = {
            "forecast_mae_scaled": forecast.item(),
            "retention_mse": retention.item(),
            "weighted_retention": weight * retention.item(),
            "lambda": weight,
            "forecast_gradient_norm": nf,
            "retention_gradient_norm": nr,
            "weighted_gradient_ratio": weight * nr / (nf + 1e-12),
            "gradient_alignment": torch.dot(a, b).item() / (nf * nr) if nf * nr else None,
            "latent_displacement_mse": (z - source).square().mean().item(),
            "epsilon_g": 1e-12,
        }
        return result
    finally:
        model.train(previous)
