import numpy as np
import pytest
import anyplotlib as apl
from anyplotlib.plot2d import Plot2D
from deapi.data_types import Result, Histogram


@pytest.fixture
def sample_result():
    image = np.random.rand(64, 64).astype(np.float32)
    hist = Histogram(min=0.0, max=1.0, bins=256, data=list(np.ones(256)))
    return Result(image=image, pixel_format=None, attributes=None, histogram=hist)


def test_result_plot_standalone_returns_figure(sample_result):
    fig = sample_result.plot()
    assert isinstance(fig, apl.Figure)


def test_result_plot_embedded_returns_plot2d(sample_result):
    fig, axs = apl.subplots(1, 2)
    result = sample_result.plot(ax=axs[0])
    assert isinstance(result, Plot2D)


def test_result_plot_kwargs_forwarded(sample_result):
    fig = sample_result.plot(cmap="viridis", vmin=0.1, vmax=0.9)
    assert isinstance(fig, apl.Figure)


def test_result_plot_no_histogram():
    image = np.random.rand(64, 64).astype(np.float32)
    result = Result(image=image, pixel_format=None, attributes=None, histogram=None)
    fig = result.plot()
    assert isinstance(fig, apl.Figure)
