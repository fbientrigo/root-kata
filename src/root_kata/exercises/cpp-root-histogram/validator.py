from root_kata.validation import case, expect, expect_close, expect_equal

def _obj(r): expect(r.get("returned object"),"build_histogram returned nullptr",actual="nullptr",expected="TH1D*")
def _shape(r):
    _obj(r); expect_equal(r["name"],"h_pt","Histogram name is wrong"); expect_equal(r["nbins"],10,"Number of bins is wrong"); expect_close(r["xmin"],0.0,message="Lower edge is wrong"); expect_close(r["xmax"],100.0,message="Upper edge is wrong")
def _filled(r):
    _obj(r); expect_close(r["entries"],3,message="Each input value should be filled once"); expect_close(r["integral"],3,message="In-range integral should be 3"); expect_close(r["mean"],20.0,message="Histogram mean is unexpected")
def _overflow(r):
    _obj(r); expect_close(r["ovf entries"],3,message="Under/overflow values still count as entries"); expect_close(r["ovf integral"],1,message="Default Integral() excludes under/overflow bins")
def grade(r): return [case("ROOT object and binning",lambda:_shape(r)),case("fills input values",lambda:_filled(r)),case("underflow and overflow semantics",lambda:_overflow(r))]
