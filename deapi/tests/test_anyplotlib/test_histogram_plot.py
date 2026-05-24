import numpy as np
import pytest
import anyplotlib as apl
from anyplotlib.plot1d import Plot1D
from deapi.data_types import Histogram


@pytest.fixture
def hist():
    return Histogram(min=0.0, max=100.0, bins=256, data=list(np.ones(256)))


def test_histogram_plot_standalone_returns_figure(hist):
    fig = hist.plot()
    assert isinstance(fig, apl.Figure)


def test_histogram_plot_embedded_returns_plot1d(hist):
    fig, ax = apl.subplots(1, 1)
    result = hist.plot(ax=ax)
    assert isinstance(result, Plot1D)


def test_histogram_plot_none_data_does_not_crash():
    hist = Histogram(min=0.0, max=100.0, bins=256, data=None)
    fig = hist.plot()
    assert isinstance(fig, apl.Figure)
