from root_kata.validation import case, expect, expect_close, expect_equal

def _status(r):
    expect_equal(r["status"], 0, "Fit should converge")

def _parameters(r):
    expect_close(r["mean"], 5.0, rel_tol=0.0, abs_tol=0.05, message="Fitted mean should recover the peak location")
    expect(r["sigma"] > 0.0, "Fitted sigma must be positive", actual=r["sigma"], expected="> 0")
    expect_close(r["sigma"], 0.8, rel_tol=0.0, abs_tol=0.05, message="Fitted sigma should recover the peak width")

def grade(r):
    return [case("fit converges", lambda: _status(r)), case("recovers peak parameters", lambda: _parameters(r))]
