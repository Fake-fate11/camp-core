// Copyright 2026 Xinchen Lin
// SPDX-License-Identifier: Apache-2.0
// Adapted from the existing autoware_trajectory_ranker CAMP prototype.
#pragma once
#include <array>
#include <filesystem>
#include <optional>
#include <string>
#include <vector>

namespace camp {
constexpr std::size_t atom_count = 16;
using Atoms = std::array<double, atom_count>;
using Status = std::array<std::string, atom_count>;
struct Result {
  std::size_t selected_row{};
  std::vector<double> scores;
  std::vector<double> active_weights;
};
// Receives whole-pool atoms from the host's decision-time materializer.
// No ROS, generator, map loader, training solver, or realized future dependency.
class Selector {
public:
  explicit Selector(const std::filesystem::path & model);
  // The full pool must match candidate_pool_k in this deployment export.
  // Status is shared across its original rows; phi is required only for Scene.
  Result select(const std::vector<Atoms> & raw, const Status & status,
                const std::vector<double> & phi = {});
  void reset() { last_result_.reset(); }
  const std::optional<Result> & last_result() const { return last_result_; }
  const std::array<double, 3> & transition_scales() const { return transition_; }
private:
  struct Head { Status status; std::vector<std::size_t> active;
                std::vector<std::vector<double>> theta; };
  std::size_t k_{}, width_{};
  bool scene_{};
  Atoms scales_{};
  std::array<double, 3> transition_{};
  std::vector<Head> heads_;
  std::optional<Result> last_result_;
};
// Flatten tokens in the frozen DP type order; true means padding, as in Python.
std::vector<double> masked_mean(const std::vector<std::vector<double>> & tokens,
                               const std::vector<bool> & padding_mask);
}  // namespace camp
