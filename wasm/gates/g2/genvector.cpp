#include <cstdio>

#include <Math/Vector4D.h>

int main() {
  const ROOT::Math::PtEtaPhiMVector muon(50.0, 1.2, 0.5, 0.105658);
  const ROOT::Math::PtEtaPhiMVector pion(12.0, -0.4, -1.0, 0.139570);
  const auto sum = muon + pion;

  std::printf("pt=%.6f eta=%.6f phi=%.6f m=%.6f\n", muon.Pt(), muon.Eta(), muon.Phi(), muon.M());
  std::printf("E=%.6f px=%.6f py=%.6f pz=%.6f\n", muon.E(), muon.Px(), muon.Py(), muon.Pz());
  std::printf("sum_m=%.6f sum_pt=%.6f\n", sum.M(), sum.Pt());
}
