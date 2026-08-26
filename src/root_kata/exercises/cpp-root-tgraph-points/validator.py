from root_kata.validation import case, expect, expect_close, expect_equal

def _count(r):
    expect(r["returned object"], "Graph must be returned")
    expect_equal(r["n"], 3, "Graph has the wrong number of points")

def _coordinates(r):
    for i, (x, y) in enumerate([(0.0, 2.0), (1.5, 3.5), (4.0, 3.0)]):
        expect_close(r[f"x{i}"], x, message="x coordinate differs")
        expect_close(r[f"y{i}"], y, message="y coordinate differs")

def grade(r):
    return [case("point count", lambda: _count(r)), case("paired coordinates", lambda: _coordinates(r))]
