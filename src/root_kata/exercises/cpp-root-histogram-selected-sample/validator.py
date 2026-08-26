from root_kata.validation import case, expect, expect_close, expect_equal

def _strict(r):
    expect(r["a returned"], "Histogram must be returned")
    expect_equal(r["name"], "h_selected", "Histogram name is wrong")
    expect_equal(r["nbins"], 5, "Histogram binning is wrong")
    expect_close(r["xmin"], 0.0, message="Histogram binning is wrong")
    expect_close(r["xmax"], 150.0, message="Histogram binning is wrong")
    expect_close(r["a entries"], 3.0, message="Strict cut should keep exactly three values")
    expect_close(r["a integral"], 3.0, message="All three selected values should be visible")
    expect_close(r["a first bin"], 0.0, message="Boundary value must not survive a strict cut")

def _range(r):
    expect(r["b returned"], "Histogram must be returned")
    expect_close(r["b entries"], 2.0, message="Selected overflow value must still count as an entry")
    expect_close(r["b integral"], 1.0, message="Only one selected value should be visible")
    expect_close(r["b overflow"], 1.0, message="The out-of-range selected value should land in overflow")

def grade(r):
    return [case("strict selection", lambda: _strict(r)), case("selection versus visible range", lambda: _range(r))]
