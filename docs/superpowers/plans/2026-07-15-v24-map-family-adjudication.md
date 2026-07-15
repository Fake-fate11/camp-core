# v24 outcome-blind map-family adjudication

## Boundary

This gate uses only frozen source bytes, the static map census, and builder
loadability receipts. It does not generate routes, candidates, labels, or
closed-loop outcomes; route census remains unopened.

## Frozen family graph

- Exact byte duplicates remain one blob node and keep every path receipt.
- Each unique blob with usable geometry becomes one graph node.
- A pair receives an undirected edge only when bbox containment >= 0.98 and
  absolute segment containment >= 0.80 at 1e-8 degree coordinate
  quantization.
- Map families are the graph's connected components.
- Builder status never creates a family edge; it only labels a component as
  loadable when at least one retained path loaded in the fixed builder smoke.
- No geometry is an unassigned source receipt, not a synthetic map family.

The rule is outcome-blind and name-blind. File names, route results, candidate
risk, and downstream evaluation cannot create, remove, or tune an edge.

## Verification

Run the focused contract tests, Python compilation, all v24 audit tests, and
`git diff --check`. Seal the execution report and every graph-pair receipt
before starting the >=80m route census.
