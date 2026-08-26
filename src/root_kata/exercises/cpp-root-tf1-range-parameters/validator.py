from root_kata.validation import case, expect, expect_close, expect_equal
import math

def _parameters(r):
    expect(r["returned object"], "Model must be returned")
    expect_equal(r["name"], "decay_model", "TF1 name is wrong")
    expect_close(r["p0"], 12.0, message="Amplitude parameter is wrong")
    expect_close(r["p1"], 2.0, message="Tau parameter is wrong")
    expect_close(r["eval0"], 12.0, message="Decay prediction is wrong")

def _domain(r):
    expect_close(r["xmin"], 0.0, message="Model range is wrong")
    expect_close(r["xmax"], 10.0, message="Model range is wrong")
    expect_close(r["eval4"], 12.0 * math.exp(-2.0), rel_tol=1e-10, abs_tol=1e-10, message="Decay prediction is wrong")

def grade(r):
    return [case("parameter meaning", lambda: _parameters(r)), case("model domain and prediction", lambda: _domain(r))]
