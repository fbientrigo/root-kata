from root_kata.validation import case, expect, expect_close, expect_equal

def _definition(r):
    expect(r["returned object"], "Model must be returned")
    expect_equal(r["name"], "calibration_model", "TF1 name is wrong")
    expect_equal(r["npar"], 2, "TF1 should have two parameters")
    expect_close(r["xmin"], 0.0, message="Model range is wrong")
    expect_close(r["xmax"], 10.0, message="Model range is wrong")
    expect_close(r["p0"], 2.0, message="Intercept parameter is wrong")
    expect_close(r["p1"], 3.0, message="Slope parameter is wrong")
    expect_close(r["eval0"], 2.0, message="Model evaluation is wrong")
    expect_close(r["eval2"], 8.0, message="Model evaluation is wrong")

def _change(r):
    expect_close(r["eval2 changed"], 0.0, message="Changing the slope should change the prediction")

def grade(r):
    return [case("model definition", lambda: _definition(r)), case("parameter change affects prediction", lambda: _change(r))]
