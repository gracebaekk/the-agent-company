#!/usr/bin/env python3
"""Precompute task instructions from Docker images and save as JSON."""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.green_agent.evaluation.task_selector import TASK_SUBSETS, get_task_image_name
from src.utils.docker_manager import DockerManager


async def extract_all_task_instructions():
    """Extract task instructions from all Docker images."""
    
    docker = DockerManager()
    all_tasks = set()
    
    # Collect all tasks from all subsets
    for subset_name, tasks in TASK_SUBSETS.items():
        all_tasks.update(tasks)
    
    print(f"Found {len(all_tasks)} unique tasks across all subsets")
    print("=" * 60)
    
    task_instructions = {}
    failed_tasks = []
    
    for i, task_name in enumerate(sorted(all_tasks), 1):
        print(f"\n[{i}/{len(all_tasks)}] Processing: {task_name}")
        
        image_name = get_task_image_name(task_name)
        
        try:
            # Pull image if needed
            print(f"  Checking/pulling image: {image_name}")
            image_available = await docker.pull_image(image_name)
            
            if not image_available:
                print(f"  ⚠️  Failed to get image, skipping")
                failed_tasks.append(task_name)
                continue
            
            # Extract instruction
            print(f"  Extracting task instruction...")
            instruction = await docker.get_task_instruction(image_name)
            
            if instruction and len(instruction) > 50:  # Valid instruction
                task_instructions[task_name] = instruction
                print(f"  ✓ Extracted ({len(instruction)} chars)")
            else:
                print(f"  ⚠️  Invalid instruction, skipping")
                failed_tasks.append(task_name)
                
        except Exception as e:
            print(f"  ✗ Error: {e}")
            failed_tasks.append(task_name)
    
    # Save to JSON
    output_dir = Path(__file__).parent  # Save to data/ directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / "task_instructions.json"
    
    with open(output_file, 'w') as f:
        json.dump(task_instructions, f, indent=2)
    
    print("\n" + "=" * 60)
    print(f"✓ Precomputation complete!")
    print(f"  Saved {len(task_instructions)} task instructions to:")
    print(f"  {output_file}")
    
    if failed_tasks:
        print(f"\n⚠️  Failed to extract {len(failed_tasks)} tasks:")
        for task in failed_tasks:
            print(f"    - {task}")
    
    return task_instructions


if __name__ == "__main__":
    print("=" * 60)
    print("PRECOMPUTING TASK INSTRUCTIONS FROM DOCKER IMAGES")
    print("=" * 60)
    print("\nThis will:")
    print("  1. Pull Docker images for all tasks")
    print("  2. Extract task instructions from each image")
    print("  3. Save them as JSON for fast access")
    print("\nThis may take 30-60 minutes depending on your connection.")
    print("You only need to run this once!\n")
    
    asyncio.run(extract_all_task_instructions())

