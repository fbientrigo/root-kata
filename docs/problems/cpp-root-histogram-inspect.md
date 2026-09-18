# Inspect a ROOT histogram

A `TH1D` is not only a picture. It stores observations in bins and also keeps summary statistics that you can inspect numerically.

You are given a histogram that is already filled. Implement:

```cpp
HistogramInspection inspect_histogram(const TH1D& hist, int bin)
```

Return four observations **without modifying the histogram**:

- the histogram's total number of entries;
- the content of the requested ROOT bin;
- the mean;
- the standard deviation.

## Observe before coding

Imagine five measurements have been filled into a histogram, but only two landed in bin 2.

Predict these two values before you edit the code:

```text
entries     = ?
bin_content = ?
```

They are different questions. `GetEntries()` describes how many observations were filled in total; `GetBinContent(bin)` describes what is represented by one particular bin.

ROOT numbers the visible x-axis bins from `1` to `GetNbinsX()`.

Your code should only inspect the supplied `TH1D`. Do not fill, reset, or rebuild it.
