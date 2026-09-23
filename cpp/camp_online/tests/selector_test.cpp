// SPDX-License-Identifier: Apache-2.0
#include "camp/selector.hpp"
#include <nlohmann/json.hpp>
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {
using Json = nlohmann::json;
using Path = std::filesystem::path;
const double nan = std::numeric_limits<double>::quiet_NaN();
const double inf = std::numeric_limits<double>::infinity();

void check(bool condition, const std::string & message) {
  if (!condition) throw std::runtime_error(message);
}

void check_close(double actual, double expected, const std::string & message) {
  check(std::isfinite(actual) && std::abs(actual - expected) < 1e-12,
        message + ": expected " + std::to_string(expected) + ", got " + std::to_string(actual));
}

void check_values(const std::vector<double> & actual, const std::vector<double> & expected,
                  const std::string & message) {
  check(actual.size() == expected.size(), message + ": size differs");
  for (std::size_t j = 0; j < actual.size(); ++j)
    check_close(actual[j], expected[j], message + " at " + std::to_string(j));
}

template<class Function> void expect_invalid(Function function, const std::string & message) {
  try {
    function();
  } catch (const std::invalid_argument &) {
    return;
  }
  throw std::runtime_error(message + ": expected invalid_argument");
}

camp::Status status() {
  camp::Status result;
  result.fill("not_applicable");
  result[0] = result[1] = "observed";
  result[2] = "typed_missing";
  return result;
}

// A deployment export fixture, not a training or model-quality benchmark.
Json model(std::size_t k, const std::string & kind,
           const std::vector<std::vector<double>> & theta) {
  const std::vector<std::string> atom_names{
    "predicted_obb_collision_exposure_fraction", "ttc_deficit_0_95s",
    "dynamic_clearance_buffer_deficit", "overspeed_integral_m2_per_s",
    "full_footprint_road_exit_severity_s", "reverse_progress_severity_m",
    "red_light_crossing_exposure_fraction", "red_stopping_margin_m2_s",
    "route_progress_shortfall_m", "longitudinal_acceleration_energy_s",
    "lateral_acceleration_energy_s", "yaw_rate_energy_s", "yaw_acceleration_energy_s",
    "longitudinal_jerk_energy_s", "jerk_magnitude_energy_s",
    "previous_plan_execution_transition_rms"};
  camp::Atoms scales;
  scales.fill(1.0);
  scales[0] = 2.0;
  scales[1] = 4.0;
  return Json{
    {"format_version", 2}, {"atom_names", atom_names}, {"candidate_pool_k", k},
    {"theta_width", theta.front().size()}, {"model_kind", kind}, {"scales", scales},
    {"transition_scales", {{"position_m", 1.0}, {"yaw_rad", 2.0},
                            {"longitudinal_velocity_mps", 3.0}}},
    {"patterns", Json::array({{{"status", status()}, {"active", {0, 1}}, {"theta", theta}}})}};
}

Path write_model(const Path & directory, const std::string & name, const Json & contents) {
  const auto path = directory / (name + ".json");
  std::ofstream stream(path);
  stream << contents.dump(2) << '\n';
  check(static_cast<bool>(stream), "cannot write test model " + path.string());
  return path;
}

std::vector<camp::Atoms> pool(std::size_t k) {
  std::vector<camp::Atoms> raw(k);
  for (auto & row : raw) {
    row.fill(nan);  // NA/missing values are not fabricated as zero observations.
    row[0] = row[1] = 0.0;
  }
  return raw;
}

void fixed(const Path & directory) {
  auto raw = pool(3);
  raw[0][0] = 2.0; raw[0][1] = 8.0;
  raw[1][0] = 6.0; raw[1][1] = 0.0;
  raw[2][0] = 80.0; raw[2][1] = 4.0;
  // Both existing Fixed encodings use only their bias. A supplied phi must not
  // activate the legacy zero-context coefficient in the width-two encoding.
  const std::vector<std::vector<std::vector<double>>> encodings{
    {{0.25}, {0.75}}, {{123.0, 0.25}, {-321.0, 0.75}}};
  for (std::size_t i = 0; i < encodings.size(); ++i) {
    camp::Selector selector(write_model(directory, "fixed-" + std::to_string(i),
                                        model(3, "fixed", encodings[i])));
    check(!selector.last_result(), "new selector has a cached result");
    const auto result = selector.select(raw, status(), {nan, inf});
    check_values(result.active_weights, {0.25, 0.75}, "Fixed bias weights");
    // Hand calculation: scale by (2,4), clip to 10, then weighted sum.
    check_values(result.scores, {1.75, 0.75, 3.25}, "Fixed scores");
    check(result.selected_row == 1, "Fixed selected row");
    check(selector.transition_scales() == std::array<double, 3>{1.0, 2.0, 3.0},
          "transition scales differ from export");
  }
}

void scene(const Path & directory) {
  camp::Selector selector(write_model(directory, "scene",
    model(3, "scene", {{-2.0, 1.0, 0.5}, {1.0, -1.0, 0.25}})));
  auto raw = pool(3);
  raw[0][0] = 2.0;
  raw[1][1] = 4.0;
  raw[2][0] = 80.0;
  const auto result = selector.select(raw, status(), {2.0, -1.0});
  // The negative weight and non-unit sum must survive unchanged. Softmax,
  // nonnegative clipping or simplex projection would change these answers.
  check_values(result.active_weights, {-4.5, 3.25}, "raw affine Scene weights");
  check_values(result.scores, {-4.5, 3.25, -45.0}, "raw affine Scene scores");
  check(result.selected_row == 2, "Scene selected row");
  const auto other_context = selector.select(raw, status(), {0.0, 0.0});
  check_values(other_context.active_weights, {0.5, 0.25}, "Scene bias context");
  check_values(other_context.scores, {0.5, 0.25, 5.0}, "Scene bias scores");
  check(other_context.selected_row == 1, "Scene context must affect selection");
}

void status_heads(const Path & directory) {
  auto contents = model(2, "fixed", {{1.0}, {0.0}});
  auto na_status = status();
  na_status[2] = "not_applicable";
  contents["patterns"].push_back({{"status", na_status}, {"active", {0, 1}},
                                   {"theta", {{0.0}, {1.0}}}});
  camp::Selector selector(write_model(directory, "status", contents));
  auto raw = pool(2);
  raw[0][1] = 4.0;
  raw[1][0] = 2.0;
  raw[0][2] = nan; raw[1][2] = inf;
  raw[0][3] = -100.0;  // Unobserved entries are not validated as observed atoms.
  check(selector.select(raw, status()).selected_row == 0, "typed_missing head");
  check(selector.select(raw, na_status).selected_row == 1, "not_applicable head");
  auto unknown_status = status();
  unknown_status[3] = "typed_missing";
  expect_invalid([&] { selector.select(raw, unknown_status); }, "unknown status pattern");

  contents["patterns"][0]["active"] = {0, 2};
  const auto invalid_path = write_model(directory, "invalid-active", contents);
  expect_invalid([&] { camp::Selector invalid(invalid_path); },
                 "active indices must equal observed indices");
}

void stable_ties(const Path & directory) {
  camp::Selector selector(write_model(directory, "ties", model(8, "fixed", {{1.0}, {0.0}})));
  auto raw = pool(8);
  for (auto & row : raw) row[0] = 20.0;
  raw[1][0] = raw[5][0] = 2.0;
  const auto result = selector.select(raw, status());
  check(result.selected_row == 1, "tie must preserve first original row");
  check_values(result.scores, {10.0, 1.0, 10.0, 10.0, 10.0, 1.0, 10.0, 10.0},
               "tie scores preserve original row order");
  for (auto & row : raw) row[0] = 2.0;
  check(selector.select(raw, status()).selected_row == 0, "all-row tie must retain row0");
}

void candidate_pool_k(const Path & directory) {
  for (const std::size_t k : {8u, 16u, 32u}) {
    // Identical weights in distinct, explicitly sized deployment exports.
    camp::Selector selector(write_model(directory, "k-" + std::to_string(k),
                                        model(k, "fixed", {{1.0}, {0.0}})));
    auto raw = pool(k);
    for (auto & row : raw) row[0] = 2.0;
    raw.back()[0] = 0.0;
    const auto result = selector.select(raw, status());
    check(result.scores.size() == k, "must score every original row");
    check(result.selected_row == k - 1, "must not score a fixed-size prefix");
    check_close(result.scores.front(), 1.0, "row0 score");
    check_close(result.scores.back(), 0.0, "last row score");
    raw.pop_back();
    expect_invalid([&] { selector.select(raw, status()); }, "shorter pool than export");
    raw.push_back(raw.front());
    raw.push_back(raw.front());
    expect_invalid([&] { selector.select(raw, status()); }, "longer pool than export");
  }
}

void invalid_inputs(const Path & directory) {
  camp::Selector selector(write_model(directory, "scene",
    model(2, "scene", {{2.0, 0.0, 0.0}, {0.0, 1.0, 0.0}})));
  auto raw = pool(2);
  expect_invalid([&] { selector.select({}, status(), {1.0, 1.0}); }, "empty pool");
  for (const auto & phi : std::vector<std::vector<double>>{
         {}, {1.0}, {1.0, 2.0, 3.0}, {nan, 0.0}, {0.0, inf}})
    expect_invalid([&] { selector.select(raw, status(), phi); }, "invalid Scene embedding");
  expect_invalid([&] { selector.select(raw, status(), {1e308, 0.0}); },
                 "overflowed affine weight");
  for (double invalid : {-1.0, nan, inf}) {
    auto bad_atoms = raw;
    bad_atoms[1][0] = invalid;
    expect_invalid([&] { selector.select(bad_atoms, status(), {1.0, 1.0}); },
                   "invalid observed atom");
  }
  camp::Selector overflow(write_model(directory, "overflow",
    model(2, "fixed", {{1e308}, {1e308}})));
  raw[0][0] = raw[0][1] = 40.0;
  expect_invalid([&] { overflow.select(raw, status()); }, "overflowed final score");
}

void reset(const Path & directory) {
  camp::Selector selector(write_model(directory, "reset", model(2, "fixed", {{1.0}, {0.0}})));
  auto raw = pool(2);
  raw[0][0] = 2.0;
  const auto result = selector.select(raw, status());
  check(selector.last_result().has_value(), "successful select must cache result");
  check(selector.last_result()->selected_row == 1, "cached selection");
  auto invalid = raw;
  invalid[0][0] = nan;
  expect_invalid([&] { selector.select(invalid, status()); }, "rejected update");
  check_values(selector.last_result()->scores, result.scores,
               "rejected input must not replace last successful result");
  selector.reset();
  check(!selector.last_result(), "reset must clear result");
  selector.reset();
  check_values(selector.select(raw, status()).scores, result.scores,
               "reset must preserve model and scales");
}

void masked_mean(const Path &) {
  check_values(camp::masked_mean({{2.0, 4.0}, {nan, inf}, {4.0, 8.0}},
                                 {false, true, false}),
               {3.0, 6.0}, "true padding mask must exclude invalid tokens");
  expect_invalid([] { camp::masked_mean({}, {}); }, "empty token stream");
  expect_invalid([] { camp::masked_mean({{1.0}}, {}); }, "mask length");
  expect_invalid([] { camp::masked_mean({{1.0}, {1.0, 2.0}}, {false, false}); },
                 "token widths");
  expect_invalid([] { camp::masked_mean({{1.0}}, {true}); }, "all tokens padded");
  expect_invalid([] { camp::masked_mean({{nan}}, {false}); }, "nonfinite valid token");
}
}  // namespace

int main(int argc, char ** argv) {
  try {
    check(argc == 3, "usage: camp_selector_tests case fixture_directory");
    using Test = std::pair<std::string, void (*)(const Path &)>;
    const std::vector<Test> tests{
      {"fixed", fixed}, {"scene", scene}, {"status", status_heads},
      {"stable_ties", stable_ties}, {"candidate_pool_k", candidate_pool_k},
      {"invalid_inputs", invalid_inputs}, {"reset", reset}, {"masked_mean", masked_mean}};
    const auto test = std::find_if(tests.begin(), tests.end(),
      [&](const Test & candidate) { return candidate.first == argv[1]; });
    check(test != tests.end(), "unknown test case");
    const Path directory(argv[2]);
    std::filesystem::create_directories(directory);
    test->second(directory);
    std::cout << test->first << " passed\n";
  } catch (const std::exception & e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
