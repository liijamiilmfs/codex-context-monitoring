# MVP-07 charting library decision

**Decision:** MVP-08 will use **Matplotlib 3.11.x** for local, static bar or
column charts. Its license is the Python Software Foundation License (the
Matplotlib license). When the dependency is approved for implementation, pin
the supported minor line as `matplotlib>=3.11,<3.12` in `pyproject.toml` and
commit the resulting `uv.lock`. Do not add it as part of this decision record.

## Scope and criteria

MVP-08 needs a local, headless renderer for in-memory usage-comparison data and
a checked-in raster or vector sample suitable for forum embedding. It does not
need an interactive browser UI, a cloud service, or telemetry. The candidates
below were assessed against Python 3.14, license, static bar rendering,
deterministic local output, maintenance, install burden, and architectural
isolation. Sources were checked on 2026-08-31.

| Candidate | Evidence and fit | Trade-off |
| -- | -- | -- |
| **Matplotlib 3.11.1** | The current PyPI release requires Python 3.11+ and explicitly publishes CPython 3.14 Windows wheels; it is licensed under the Python Software Foundation License and lists three maintainers. [PyPI metadata](https://pypi.org/project/matplotlib/3.11.1/) The project documents non-interactive Agg, PDF, PS, and SVG backends; Agg writes PNG and PDF/SVG are vector outputs. [Backends](https://matplotlib.org/stable/users/explain/figure/backends.html) Its documented bar-chart example and `Figure.savefig` support direct rendering from in-memory values to a local image or vector file. [Bar-chart example](https://matplotlib.org/stable/gallery/lines_bars_and_markers/barchart.html), [`savefig`](https://matplotlib.org/stable/api/_as_gen/matplotlib.figure.Figure.savefig.html) The actively maintained 3.11.1 release was published on 2026-07-18. [Release](https://github.com/matplotlib/matplotlib/releases/tag/v3.11.1) | One runtime package with native wheel dependencies; it is more than a tiny drawing helper, but the static backends need no GUI toolkit or browser. |
| **Plotly.py** | Plotly.py is MIT-licensed, requires Python 3.8+, and ships a universal Python 3 wheel, so it is compatible with this project’s Python 3.14 floor. [PyPI metadata](https://pypi.org/project/plotly/6.5.2/) It can create bars from in-memory data and write PNG, SVG, and PDF. [Static export](https://plotly.com/python/static-image-export/) Its official repository describes it as an interactive Python graphing library and has current releases. [Repository](https://github.com/plotly/plotly.py), [releases](https://github.com/plotly/plotly.py/releases) | Static export requires the additional `kaleido` package and Chrome or Chromium; this expands the local/headless operational footprint. [Static-export requirements](https://plotly.com/python/static-image-export/) |

## Rationale

Matplotlib is the smallest reasonable MVP fit: it meets the required local
PNG/SVG/PDF output without a browser runtime or an additional export package,
while directly supporting the project’s Python 3.14 environment. Plotly.py
remains a credible future option if interactive browser-based exploration
becomes a requirement, but that is outside this MVP.

## MVP-08 boundary

Under R0S-ARCH-LAYERS `2.0.0-rc.2`, MVP-08 must keep Matplotlib inside a
vendor-specific implementation boundary. The application must own one narrow
chart capability whose inputs and outputs use only first-party Models or
Contracts (for example, application chart data and an application-owned output
representation). Controllers, Services, Transformers, and Models must not
import Matplotlib types. The implementation boundary may translate that narrow
capability into Matplotlib calls and renderer settings. This decision does not
design or implement that abstraction.

## Consequences

MVP-08 may add the approved dependency and its lockfile update, implement the
boundary, and generate a sanitized sample artifact. It must use a
non-interactive static backend and keep output settings explicit so the sample
is stable enough to check in and embed. This note adds no dependency, UI,
cloud service, telemetry, artifact, or runtime code.
