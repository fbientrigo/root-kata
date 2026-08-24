from root_kata.validation import case, expect_equal


def grade(r):
    return [
        case("prints something", lambda: expect_equal(r["prints something"], True)),
        case("exact output", lambda: expect_equal(r["exact output"], True)),
    ]
