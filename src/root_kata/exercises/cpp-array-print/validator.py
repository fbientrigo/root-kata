from root_kata.validation import case, expect_equal


def grade(r):
    return [
        case("value count", lambda: expect_equal(r["value count"], 3)),
        case("first value", lambda: expect_equal(r["first value"], 4)),
        case("second value", lambda: expect_equal(r["second value"], 8)),
        case("third value", lambda: expect_equal(r["third value"], 15)),
    ]
