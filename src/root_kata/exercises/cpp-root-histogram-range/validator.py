from root_kata.validation import case, expect, expect_close, expect_equal

def _range(r):
    expect(r["returned object"], "Histogram must be returned")
    expect_equal(r["name"], "h_calibration", "Histogram name is wrong")
    expect_equal(r["nbins"], 11, "Expected 11 visible bins from 0 to 110")
    expect_close(r["xmin"], 0.0)
    expect_close(r["xmax"], 110.0, message="Expected 11 visible bins from 0 to 110")
    expect_close(r["bin width"], 10.0, message="Visible bins must stay 10 units wide")

def _contents(r):
    expect_close(r["entries"], 11.0, message="Every calibration value should be filled once")
    expect_close(r["visible integral"], 11.0, message="All calibration values should be visible")
    expect_close(r["underflow"], 0.0, message="Calibration sample should not underflow")
    expect_close(r["overflow"], 0.0, message="Calibration sample should not overflow")

def grade(r):
    return [case("range keeps boundary visible", lambda: _range(r)), case("fills every measurement", lambda: _contents(r))]
