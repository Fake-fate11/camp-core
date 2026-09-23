// SPDX-License-Identifier: Apache-2.0
#include "camp/selector.hpp"
#include <nlohmann/json.hpp>
#include <fstream>
#include <iostream>
#include <limits>
int main(int argc, char ** argv) {
  try {
    if (argc != 3) throw std::invalid_argument("usage: camp_score model.json ticks.json");
    camp::Selector selector(argv[1]);
    std::ifstream stream(argv[2]); auto ticks = nlohmann::json::parse(stream);
    nlohmann::json output = nlohmann::json::array();
    for (const auto & tick : ticks) {
      std::vector<camp::Atoms> atoms;
      for (const auto & row : tick.at("raw_atoms")) {
        if (!row.is_array() || row.size() != camp::atom_count)
          throw std::invalid_argument("each raw_atoms row must contain 16 entries");
        camp::Atoms a;
        for (std::size_t j = 0; j < a.size(); ++j)
          a[j] = row[j].is_null() ? std::numeric_limits<double>::quiet_NaN() : row[j].get<double>();
        atoms.push_back(a);
      }
      const auto phi = tick.contains("tokens") ? camp::masked_mean(
          tick.at("tokens").get<std::vector<std::vector<double>>>(),
          tick.at("padding_mask").get<std::vector<bool>>()) :
        tick.value("phi", std::vector<double>{});
      const auto r = selector.select(atoms, tick.at("status").get<camp::Status>(), phi);
      output.push_back({{"selected_row", r.selected_row}, {"scores", r.scores},
                        {"active_weights", r.active_weights}});
      selector.reset();
      if (selector.last_result()) throw std::runtime_error("reset failed");
    }
    std::cout << output.dump() << '\n';
  } catch (const std::exception & e) { std::cerr << e.what() << '\n'; return 1; }
}
