"""
lmfit models
"""

from lmfit import Model
from lmfit.models import (
    GaussianModel, LorentzianModel, VoigtModel, PseudoVoigtModel, LinearModel, ExponentialModel,
    SineModel
)

__all__ = ['PEAK_PARS', 'METHODS', 'get_peak_model', 'get_background_model', 'get_default_model',
           'PEAK_MODELS', 'BACKGROUND_MODELS']

# https://lmfit.github.io/lmfit-py/builtin_models.html#peak-like-models

ModelType = type[GaussianModel | LorentzianModel | VoigtModel | PseudoVoigtModel | LinearModel | ExponentialModel | SineModel]

MODELS: dict[str, type[ModelType]] = {
    'gaussian': GaussianModel,
    'lorentz': LorentzianModel,
    'voight': VoigtModel,
    'pvoight': PseudoVoigtModel,
    'linear': LinearModel,
    'exponential': ExponentialModel,
    'SineModel': SineModel,
}  # list of available lmfit models

PEAK_MODELS: dict[str, list[str]] = {
    'gaussian': ['gaussian', 'gauss'],
    'voight': ['voight', 'voight model'],
    'pvoight': ['pseudovoight', 'pvoight'],
    'lorentz': ['lorentz', 'lorentzian', 'lor'],
}  # alternative names for peaks

BACKGROUND_MODELS: dict[str, list[str]] = {
    'linear': ['flat', 'slope', 'linear', 'line', 'straight'],
    'exponential': ['exponential', 'curve']
}  # alternative names for background models

DEFAULT_MODEL = 'gaussian'
DEFAULT_BACKGROUND = 'linear'

# https://lmfit.github.io/lmfit-py/fitting.html#fit-methods-table
METHODS: dict[str, str] = {
    'leastsq': 'Levenberg-Marquardt',
    'nelder': 'Nelder-Mead',
    'lbfgsb': 'L-BFGS-B',
    'powell': 'Powell',
    'cg': 'Conjugate Gradient',
    'newton': 'Newton-CG',
    'cobyla': 'COBYLA',
    'bfgsb': 'BFGS',
    'tnc': 'Truncated Newton',
    'trust-ncg': 'Newton CG trust-region',
    'trust-exact': 'Exact trust-region',
    'trust-krylov': 'Newton GLTR trust-region',
    'trust-constr': 'Constrained trust-region',
    'dogleg': 'Dogleg',
    'slsqp': 'Sequential Linear Squares Programming',
    'differential_evolution': 'Differential Evolution',
    'brute': 'Brute force method',
    'basinhopping': 'Basinhopping',
    'ampgo': 'Adaptive Memory Programming for Global Optimization',
    'shgo': 'Simplicial Homology Global Ooptimization',
    'dual_annealing': 'Dual Annealing',
    'emcee': 'Maximum likelihood via Monte-Carlo Markov Chain',
}

# Peak parameter names
PEAK_PARS = ['amplitude', 'center', 'height', 'fwhm']


def get_peak_model(name: str) -> type[ModelType]:
    """Get peak model by name."""
    model: type[ModelType] | None = None
    for model_name, names in PEAK_MODELS.items():
        if name.lower() in names:
            model = MODELS[model_name]
    if model is None:
        raise ValueError(f"Peak model '{name}' not found")
    return model


def get_background_model(name: str) -> type[ModelType]:
    """Get background model by name."""
    model: type[ModelType] | None = None
    for model_name, names in BACKGROUND_MODELS.items():
        if name.lower() in names:
            model = MODELS[model_name]
    if model is None:
        raise ValueError(f"Background model '{name}' not found")
    return model


def get_default_model(peak: str = DEFAULT_MODEL, background: str = DEFAULT_BACKGROUND) -> Model:
    """Return a single peak lmfit model"""
    model = get_peak_model(peak)
    bkg = get_background_model(background)
    return model() + bkg()

