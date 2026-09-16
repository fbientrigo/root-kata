// P1 probe: TFormula-backed TF1, and TGraph. Same shape as the P0 probe --
// every value printed at %.17g so native and wasm ROOT can be diffed exactly.
#include "TF1.h"
#include "TGraph.h"
#include "TMath.h"
#include <cstdio>

#define P(label, v) printf("%s = %.17g\n", label, (double)(v))

int main() {
   // A formula string, which TFormula compiles through the interpreter.
   TF1 lin("lin", "[0]+[1]*x", 0, 10);
   lin.SetParameters(1.0, 2.0);
   P("lin.eval(3)", lin.Eval(3.0));
   P("lin.eval(0)", lin.Eval(0.0));
   P("lin.eval(9.5)", lin.Eval(9.5));
   P("lin.npar", lin.GetNpar());
   P("lin.ndim", lin.GetNdim());
   P("lin.xmin", lin.GetXmin());
   P("lin.xmax", lin.GetXmax());
   P("lin.par0", lin.GetParameter(0));
   P("lin.par1", lin.GetParameter(1));
   lin.SetParameter(1, 0.5);
   P("lin.eval(4)after", lin.Eval(4.0));

   // A named formula, resolved by TFormula's own shortcut table.
   TF1 g("g", "gaus", -5, 5);
   g.SetParameters(2.0, 0.5, 1.5);
   P("gaus.eval(0.5)", g.Eval(0.5));
   P("gaus.eval(-1)", g.Eval(-1.0));
   P("gaus.npar", g.GetNpar());

   // An expression with a TMath call, which needs the real ROOT headers.
   TF1 m("m", "TMath::Sqrt(x)+[0]", 0, 100);
   m.SetParameter(0, 1.25);
   P("sqrt.eval(16)", m.Eval(16.0));

   // Polynomial shorthand.
   TF1 p("p", "pol2", -3, 3);
   p.SetParameters(1.0, -2.0, 0.5);
   P("pol2.eval(2)", p.Eval(2.0));
   P("pol2.npar", p.GetNpar());

   // TGraph: no interpreter needed, but it shares the Hist closure.
   double x[5] = {0.0, 1.0, 2.0, 3.0, 4.0};
   double y[5] = {0.0, 1.0, 4.0, 9.0, 16.0};
   TGraph gr(5, x, y);
   P("graph.n", gr.GetN());
   P("graph.eval(2.5)", gr.Eval(2.5));
   double gx = 0.0, gy = 0.0;
   gr.GetPoint(3, gx, gy);
   P("graph.x3", gx);
   P("graph.y3", gy);
   P("graph.mean_y", gr.GetMean(2));
   return 0;
}
