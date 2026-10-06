#!/usr/bin/env python3
import argparse
import dataclasses
import json
import sys
from pathlib import Path
import torch
from torch.utils.data import DataLoader

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core_perception.multi_agent_dataset import (
    MultiAgentTrajectoryDataset,
    collate_multi_agent_trajectory,
    split_sample_paths,
)
from scripts.validate_target_metrics import (
    load_checkpoint,
    evaluate_model,
    resolve_device,
)

def main():
    parser = argparse.ArgumentParser(description="Tune Adaptive Radius parameters (r_base and alpha).")
    parser.add_argument("--checkpoint", required=True, help="Path to checkpoint .pt file")
    parser.add_argument("--data-dir", required=True, nargs="+", help="Dataset directories")
    parser.add_argument("--test-ratio", type=float, default=0.2, help="Test ratio")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size")
    parser.add_argument("--device", default="auto", help="Device")
    args = parser.parse_args()

    device = resolve_device(args.device)
    model, checkpoint = load_checkpoint(Path(args.checkpoint), device)
    
    if not getattr(model.config, "enable_adaptive_radius", False):
        print("Warning: The checkpoint was not trained with enable_adaptive_radius=True.")
        print("Enabling it for tuning...")
        model.config = dataclasses.replace(model.config, enable_adaptive_radius=True)
    
    # Load dataset
    print("Loading dataset...")
    data_dirs = [Path(d).resolve() for d in args.data_dir]
    loaded_datasets = [MultiAgentTrajectoryDataset(d) for d in data_dirs]
    sample_paths = [p for ds in loaded_datasets for p in ds.sample_paths]
    _, test_paths = split_sample_paths(sample_paths, train_ratio=1.0 - args.test_ratio, seed=42)
    test_dataset = MultiAgentTrajectoryDataset(data_dirs[0], sample_files=test_paths)
    test_loader = DataLoader(
        test_dataset, 
        batch_size=args.batch_size, 
        shuffle=False, 
        collate_fn=collate_multi_agent_trajectory,
        pin_memory=device.type == "cuda"
    )

    # Grid search parameters
    r_base_grid = [10.0, 15.0, 20.0, 25.0, 30.0]
    alpha_grid = [0.1, 0.3, 0.5, 0.7, 1.0]

    results = []
    best_ade = float("inf")
    best_params = None

    print(f"\nStarting Grid Search over {len(r_base_grid)}x{len(alpha_grid)} combinations...")
    print("-" * 65)
    print(f"{'radius_base':<12} | {'radius_alpha':<12} | {'minADE (m)':<12} | {'minFDE (m)':<12} | {'MissRate':<10}")
    print("-" * 65)

    for r_base in r_base_grid:
        for alpha in alpha_grid:
            # Override config in memory
            model.config = dataclasses.replace(model.config, radius_base=r_base, radius_alpha=alpha)
            
            # Evaluate
            metrics, _ = evaluate_model(
                model=model,
                loader=test_loader,
                device=device,
                enable_multimodal=getattr(model.config, "enable_multimodal", False),
                per_town_metrics=False,
            )
            
            ade = metrics["minADE"]
            fde = metrics["minFDE"]
            mr = metrics["MissRate"]
            
            print(f"{r_base:<12.1f} | {alpha:<12.2f} | {ade:<12.4f} | {fde:<12.4f} | {mr:<10.4f}")
            
            results.append({
                "radius_base": r_base,
                "radius_alpha": alpha,
                "minADE": ade,
                "minFDE": fde,
                "MissRate": mr
            })
            
            if ade < best_ade:
                best_ade = ade
                best_params = (r_base, alpha)

    print("-" * 65)
    print(f"Best parameters: radius_base={best_params[0]:.1f}, radius_alpha={best_params[1]:.2f}")
    print(f"Best minADE:     {best_ade:.4f} m")
    
    # Save tuning summary
    output_path = Path("outputs/tuning_adaptive_radius.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump({
            "best_params": {"radius_base": best_params[0], "radius_alpha": best_params[1]},
            "best_minADE": best_ade,
            "grid_results": results
        }, f, indent=2)
    print(f"Results saved to {output_path}")

if __name__ == "__main__":
    main()
