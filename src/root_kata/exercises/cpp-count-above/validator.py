from root_kata.validation import case, expect_equal


def grade(r):
    return [
        case("mixed values", lambda: expect_equal(r["mixed values"], 1, "Only 50 should pass the cut")),
        case("strict boundary", lambda: expect_equal(r["strict boundary"], 1, "Values equal to the threshold must not pass")),
        case("empty input", lambda: expect_equal(r["empty input"], 0, "An empty sample has zero passing values")),
        case("negative threshold", lambda: expect_equal(r["negative threshold"], 2, "0 and 2 are strictly greater than -1")),
    ]
