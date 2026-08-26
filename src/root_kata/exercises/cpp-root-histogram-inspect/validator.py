from root_kata.validation import case, expect_close


def _entries_and_bins(r):
    expect_close(r["entries"], 5.0, message="Expected 5 total entries")
    expect_close(r["bin2 content"], 2.0, message="Expected 2 entries in ROOT bin 2")
    expect_close(r["bin3 content"], 0.0, message="Expected an empty ROOT bin 3")


def _statistics(r):
    expect_close(r["mean"], 2.04, rel_tol=1e-8, abs_tol=1e-8,
                 message="Histogram mean does not match the filled observations")
    expect_close(r["stddev"], 1.333566, rel_tol=1e-5, abs_tol=1e-5,
                 message="Histogram standard deviation does not match the filled observations")


def grade(r):
    return [
        case("entries versus bin contents", lambda: _entries_and_bins(r)),
        case("summary statistics", lambda: _statistics(r)),
    ]
