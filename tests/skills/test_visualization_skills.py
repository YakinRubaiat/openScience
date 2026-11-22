"""Tests for the optional-dependency visualization skills."""

import os

import numpy as np
import pandas as pd
import pytest

from openscience.skills import get_skill, list_skills
from openscience.skills._common import has_module
from openscience.skills.visualization import (
    accessibility,
    animation,
    cairosvg_skill,
    ffmpeg_skill,
    ggplot_translator,
    interactive,
    plotly_skill,
    plotnine_skill,
    style_sheets,
    vector,
)

pytestmark = pytest.mark.skipif(
    not has_module("matplotlib"), reason="matplotlib required")

DF = pd.DataFrame({
    "x": [1.0, 2.0, 3.0, 4.0],
    "y": [2.0, 1.0, 4.0, 3.0],
    "z": [5.0, 3.0, 2.0, 6.0],
    "group": ["a", "a", "b", "b"],
})

VALID_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="100" '
             'height="50"><rect width="100" height="50" fill="#0072B2"/>'
             '</svg>')
VALID_SVG_2 = ('<svg xmlns="http://www.w3.org/2000/svg" width="80" '
               'height="40"><circle cx="40" cy="20" r="15" fill="#D55E00"/>'
               '</svg>')


# ---------------------------------------------------------------------------
# registration
# ---------------------------------------------------------------------------
def test_all_skills_registered():
    for name in ("plotly", "interactive_viz", "style_sheets",
                 "accessibility_checking", "cairosvg", "vector_editing",
                 "matplotlib_animation", "ffmpeg", "plotnine",
                 "ggplot_syntax"):
        assert get_skill(name) is not None, f"{name} not registered"


# ---------------------------------------------------------------------------
# plotly
# ---------------------------------------------------------------------------
def test_plotly_capabilities():
    out = plotly_skill.run(operation="list_capabilities")
    assert out["status"] == "ok"
    assert out["plotly_installed"] == has_module("plotly")
    assert "operations" in out


@pytest.mark.skipif(has_module("plotly"), reason="plotly installed")
def test_plotly_missing_raises_clear_error():
    with pytest.raises(RuntimeError, match="pip install plotly"):
        plotly_skill.run(operation="scatter", x=[1, 2], y=[1, 2])


@pytest.mark.skipif(not has_module("plotly"), reason="plotly not installed")
def test_plotly_scatter_and_html(tmp_path):
    out = plotly_skill.run(operation="scatter", x=[1, 2, 3], y=[3, 1, 2],
                           output_path=str(tmp_path / "s.html"))
    assert os.path.exists(out["saved_to"])


# ---------------------------------------------------------------------------
# interactive_viz
# ---------------------------------------------------------------------------
def test_interactive_scatter_matrix(tmp_path):
    out = interactive.run(operation="scatter_matrix_html", data=DF,
                          output_path=str(tmp_path / "sm.html"))
    assert os.path.exists(out["saved_to"])
    assert out["backend"] in ("plotly", "matplotlib")


def test_interactive_heatmap(tmp_path):
    out = interactive.run(operation="heatmap_html", data=DF[["x", "y", "z"]],
                          output_path=str(tmp_path / "hm.html"))
    assert os.path.exists(out["saved_to"])
    assert b"<html" in (tmp_path / "hm.html").read_bytes().lower()


def test_interactive_heatmap_includes_base64_png_without_plotly(tmp_path):
    if has_module("plotly"):
        pytest.skip("only meaningful without plotly")
    out = interactive.run(operation="heatmap_html", data=DF[["x", "y"]],
                          output_path=str(tmp_path / "hm2.html"))
    assert out["backend"] == "matplotlib"
    assert "base64" in (tmp_path / "hm2.html").read_text()


def test_interactive_save_matplotlib_fig(tmp_path):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    ax.plot([1, 2], [1, 2])
    out = interactive.run(operation="save", fig=fig,
                          output_path=str(tmp_path / "fig.html"))
    assert os.path.exists(out["saved_to"])


# ---------------------------------------------------------------------------
# style_sheets
# ---------------------------------------------------------------------------
def test_style_list():
    out = style_sheets.run(operation="list_styles")
    assert {"nature", "science", "ieee", "minimal"} <= set(out["styles"])


def test_rcparams_dict():
    out = style_sheets.run(operation="rcparams_dict", name="ieee")
    assert out["rcparams"]["font.family"] == "serif"
    with pytest.raises(ValueError):
        style_sheets.run(operation="rcparams_dict", name="nope")


def test_style_apply():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    ax.plot([1, 2], [1, 2])
    out = style_sheets.run(operation="apply", name="nature", ax=ax)
    assert out["status"] == "ok"
    assert plt.rcParams["font.size"] == 7
    assert not ax.spines["top"].get_visible()


# ---------------------------------------------------------------------------
# accessibility_checking
# ---------------------------------------------------------------------------
def test_contrast_ratio_black_white():
    out = accessibility.run(operation="contrast_ratio", color1="#000000",
                            color2="#FFFFFF")
    assert out["contrast_ratio"] == pytest.approx(21.0, abs=0.05)
    assert out["wcag_aa_normal"] and out["wcag_aaa_normal"]


def test_contrast_ratio_same_color():
    out = accessibility.run(operation="contrast_ratio", color1="#FF0000",
                            color2="#FF0000")
    assert out["contrast_ratio"] == pytest.approx(1.0, abs=0.01)
    assert not out["wcag_aa_large"]


def test_simulate_cb():
    out = accessibility.run(operation="simulate_cb",
                            colors=["#E69F00"], deficiency="deuteranopia")
    assert out["transformed"]["#E69F00"].startswith("#")
    assert out["transformed"]["#E69F00"] != "#E69F00"


def test_check_palette_okabe_ito_safe():
    out = accessibility.run(operation="check_palette",
                            colors=["#0072B2", "#D55E00", "#009E73"])
    assert out["n_colors"] == 3
    assert "deuteranopia" in out["min_pairwise_distance"]
    assert out["min_pairwise_distance"]["deuteranopia"] > 0.1


def test_check_palette_unsafe_pair():
    # near-identical reds should collapse under protanopia/deuteranopia
    out = accessibility.run(operation="check_palette",
                            colors=["#FF0000", "#FE0001"])
    assert not out["colorblind_safe"]


# ---------------------------------------------------------------------------
# cairosvg
# ---------------------------------------------------------------------------
def test_validate_svg_ok():
    out = cairosvg_skill.run(operation="validate_svg", svg_string=VALID_SVG)
    assert out["valid"]
    assert out["width"] == "100"
    assert out["element_count"] >= 2


def test_validate_svg_malformed():
    out = cairosvg_skill.run(operation="validate_svg",
                             svg_string="<svg><broken")
    assert not out["valid"]
    assert "error" in out


def test_validate_svg_file(tmp_path):
    p = tmp_path / "a.svg"
    p.write_text(VALID_SVG)
    out = cairosvg_skill.run(operation="validate_svg", svg_path=str(p))
    assert out["valid"]


@pytest.mark.skipif(has_module("cairosvg"), reason="cairosvg installed")
def test_svg2png_missing_raises(tmp_path):
    with pytest.raises(RuntimeError, match="pip install cairosvg"):
        cairosvg_skill.run(operation="svg2png", svg_string=VALID_SVG,
                           output_path=str(tmp_path / "o.png"))


@pytest.mark.skipif(not has_module("cairosvg"), reason="cairosvg not installed")
def test_svg2png(tmp_path):
    out = cairosvg_skill.run(operation="svg2png", svg_string=VALID_SVG,
                             output_path=str(tmp_path / "o.png"))
    assert os.path.exists(out["saved_to"])


# ---------------------------------------------------------------------------
# vector_editing
# ---------------------------------------------------------------------------
def test_vector_optimize(tmp_path):
    svg = ('<svg xmlns="http://www.w3.org/2000/svg">\n'
           '<!-- comment -->\n<metadata>junk</metadata>\n'
           '<rect width="10" height="10"/>\n</svg>')
    out = vector.run(operation="optimize", svg_string=svg,
                     output_path=str(tmp_path / "opt.svg"))
    assert out["bytes_after"] < out["bytes_before"]
    text = (tmp_path / "opt.svg").read_text()
    assert "metadata" not in text and "comment" not in text


def test_vector_merge_side_by_side(tmp_path):
    out = vector.run(operation="merge_svgs",
                     inputs=[VALID_SVG, VALID_SVG_2],
                     output_path=str(tmp_path / "m.svg"))
    assert out["n_merged"] == 2
    assert out["width"] == pytest.approx(190.0)  # 100 + 80 + gap 10
    text = (tmp_path / "m.svg").read_text()
    assert "translate(" in text
    import xml.etree.ElementTree as ET

    assert ET.fromstring(text).tag.endswith("svg")


def test_vector_to_bytes():
    out = vector.run(operation="to_bytes", svg_string=VALID_SVG)
    assert out["svg_bytes"].startswith(b"<svg")
    assert out["n_bytes"] == len(VALID_SVG.encode("utf-8"))


# ---------------------------------------------------------------------------
# matplotlib_animation
# ---------------------------------------------------------------------------
def test_frames_only(tmp_path):
    out = animation.run(operation="frames_only", n_frames=3,
                        output_dir=str(tmp_path / "frames"))
    assert out["n_frames"] == 3
    assert len(out["frames"]) == 3
    assert all(os.path.exists(p) for p in out["frames"])


def test_line_race(tmp_path):
    out = animation.run(operation="line_race",
                        data=pd.DataFrame({"a": [1, 2, 3, 4],
                                           "b": [4, 3, 2, 1]}),
                        n_steps=4,
                        output_path=str(tmp_path / "race.gif"))
    if has_module("PIL"):
        assert out["status"] == "ok"
        assert os.path.exists(out["saved_to"])
    else:
        assert out["status"] == "unavailable"
        assert "pillow" in out["reason"]
        assert len(out["frames"]) == 4
        assert all(os.path.exists(p) for p in out["frames"])


# ---------------------------------------------------------------------------
# ffmpeg
# ---------------------------------------------------------------------------
def test_ffmpeg_graceful_or_encodes(tmp_path):
    import shutil

    out = ffmpeg_skill.run(operation="encode",
                           input=str(tmp_path / "nope_%03d.png"),
                           output_path=str(tmp_path / "o.mp4"), fps=2)
    if shutil.which("ffmpeg"):
        assert out["status"] in ("ok", "error")  # no frames -> ffmpeg error
    else:
        assert out["status"] == "unavailable"
        assert "ffmpeg" in out["reason"]


def test_ffmpeg_probe_graceful(tmp_path):
    import shutil

    out = ffmpeg_skill.run(operation="probe", path=str(tmp_path / "x.mp4"))
    if shutil.which("ffprobe"):
        assert out["status"] == "error"  # file does not exist
    else:
        assert out["status"] == "unavailable"
        assert "ffprobe" in out["reason"]


def test_frames_to_video_requires_input():
    import shutil

    if not shutil.which("ffmpeg"):
        out = ffmpeg_skill.run(operation="frames_to_video",
                               frames_dir="/tmp/frames_x")
        assert out["status"] == "unavailable"
    else:
        with pytest.raises((ValueError, Exception)):
            ffmpeg_skill.run(operation="frames_to_video")


# ---------------------------------------------------------------------------
# plotnine
# ---------------------------------------------------------------------------
@pytest.mark.skipif(has_module("plotnine"), reason="plotnine installed")
def test_plotnine_missing_raises():
    with pytest.raises(RuntimeError, match="pip install plotnine"):
        plotnine_skill.run(operation="ggplot_scatter")
    out = plotnine_skill.run(operation="capabilities")
    assert out["plotnine_installed"] is False


@pytest.mark.skipif(not has_module("plotnine"), reason="plotnine not installed")
def test_plotnine_scatter(tmp_path):
    out = plotnine_skill.run(operation="ggplot_scatter", data=DF, x="x",
                             y="y", color="group",
                             output_path=str(tmp_path / "g.png"))
    assert os.path.exists(out["saved_to"])


# ---------------------------------------------------------------------------
# ggplot_syntax translator
# ---------------------------------------------------------------------------
def test_ggplot_translate_generates_code():
    out = ggplot_translator.run(
        operation="translate",
        code="ggplot(df) + geom_point(aes(x, y))")
    assert "ax.scatter" in out["code"]
    assert out["n_geoms"] == 1


def test_ggplot_translate_and_save(tmp_path):
    out = ggplot_translator.run(
        operation="translate",
        code="ggplot(df) + geom_point(aes(x, y))",
        data=DF, output_path=str(tmp_path / "p.png"))
    assert os.path.exists(out["saved_to"])


def test_ggplot_translate_unsupported_geom_reported():
    out = ggplot_translator.run(
        operation="translate",
        code="ggplot(df) + geom_violin(aes(x, y)) + geom_line(aes(x, y))")
    assert out["unsupported"] == ["geom_violin"]
    assert "ax.plot" in out["code"]


def test_ggplot_translate_requires_geom():
    with pytest.raises(ValueError):
        ggplot_translator.run(operation="translate", code="ggplot(df)")


def test_ggplot_help():
    out = ggplot_translator.run(operation="help")
    assert "geom_point" in out["supported_geoms"]


def test_registry_lists_new_skills():
    names = list_skills()
    assert "interactive_viz" in names
    assert "ggplot_syntax" in names
