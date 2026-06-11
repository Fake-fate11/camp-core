import os
import pickle
import json
import numpy as np

def main():
    cache_path = "data/cached_eval_batch.pkl" # Can use eval or train cache for scaling
    output_path = "models/production/atom_scales.json"
    
    if not os.path.exists(cache_path):
        print(f"Error: {cache_path} not found. Run cache_dataset.py first.")
        return
        
    print(f"Loading cached scenarios from {cache_path} to compute atom scales...")
    with open(cache_path, "rb") as f:
        scenarios = pickle.load(f)
        
    if len(scenarios) == 0:
        print("Empty cache.")
        return
        
    # Gather all atoms
    all_atoms = []
    for sc in scenarios:
        all_atoms.append(sc["atoms"]) # [K, R]
        
    atoms_tensor = np.concatenate(all_atoms, axis=0) # [N*K, R]
    
    # We use the 99th percentile of raw scale to aggressively compress outlier ranges
    # while providing a strong non-zero floor to prevent dividing by tiny fractions.
    percentiles = np.percentile(np.abs(atoms_tensor), 99, axis=0)
    percentiles = np.maximum(percentiles, 1.0)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(percentiles.tolist(), f, indent=4)
        
    print(f"Computed atom scales (99th percentile): {np.round(percentiles, 3)}")
    print(f"Saved to {output_path}. Models will now automatically normalize atoms.")

if __name__ == "__main__":
    main()
