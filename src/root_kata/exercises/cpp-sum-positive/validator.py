from root_kata.validation import case, expect_close


def grade(r):
    return [
        case("mixed signs",      lambda: expect_close(r["mixed signs"], 8)),
        case("all non-positive", lambda: expect_close(r["all non-positive"], 0)),
        case("empty input",      lambda: expect_close(r["empty input"], 0)),
        case("floats",           lambda: expect_close(r["floats"], 3.75)),
    ]
