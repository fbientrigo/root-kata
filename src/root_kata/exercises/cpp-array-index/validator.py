from root_kata.validation import case, expect_equal


def grade(r):
    return [
        case("second value", lambda: expect_equal(r["second value"], 20)),
    ]
