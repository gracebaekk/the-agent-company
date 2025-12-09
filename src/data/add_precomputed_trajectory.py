#!/usr/bin/env python3
"""Add a precomputed trajectory to the repository."""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

TRAJECTORIES_DIR = Path(__file__).parent / "trajectories"


def add_trajectory(trajectory_file: str, task_name: str = None):
    """
    Add a precomputed trajectory file.
    
    Args:
        trajectory_file: Path to trajectory JSON file
        task_name: Optional task name (if not provided, inferred from filename)
    """
    trajectory_path = Path(trajectory_file)
    
    if not trajectory_path.exists():
        print(f"❌ File not found: {trajectory_file}")
        return False
    
    # Load and validate trajectory
    try:
        with open(trajectory_path, 'r') as f:
            trajectory = json.load(f)
        
        # Extract task name if not provided
        if not task_name:
            task_name = trajectory.get('task_name')
            if not task_name:
                # Try to infer from filename
                task_name = trajectory_path.stem.replace('traj_', '').replace('.json', '')
        
        if not task_name:
            print("❌ Could not determine task name. Please provide --task-name")
            return False
        
        # Ensure trajectories directory exists
        TRAJECTORIES_DIR.mkdir(parents=True, exist_ok=True)
        
        # Save to precomputed trajectories
        output_path = TRAJECTORIES_DIR / f"{task_name}.json"
        
        # Ensure trajectory has task_name
        trajectory['task_name'] = task_name
        
        with open(output_path, 'w') as f:
            json.dump(trajectory, f, indent=2)
        
        print(f"✓ Added precomputed trajectory:")
        print(f"  Task: {task_name}")
        print(f"  Source: {trajectory_file}")
        print(f"  Saved to: {output_path}")
        
        # Show trajectory info
        if isinstance(trajectory, list):
            print(f"  Actions: {len(trajectory)}")
        elif isinstance(trajectory, dict):
            actions = trajectory.get('actions', [])
            messages = trajectory.get('messages', [])
            print(f"  Actions: {len(actions)}")
            print(f"  Messages: {len(messages)}")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Add precomputed trajectory")
    parser.add_argument("trajectory_file", help="Path to trajectory JSON file")
    parser.add_argument("--task-name", help="Task name (if not in trajectory)")
    
    args = parser.parse_args()
    
    success = add_trajectory(args.trajectory_file, args.task_name)
    sys.exit(0 if success else 1)

