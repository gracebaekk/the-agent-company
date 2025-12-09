"""Custom scoring strategies for TAC evaluation."""

from typing import List, Callable, Optional
import sys
import os

# Add TAC framework to path (now 2 levels up from evaluation/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../external/tac/workspaces/base_image"))

from scoring import Checkpoint, Result


def weighted_checkpoint_scoring(weights: List[float]) -> Callable[[List[Checkpoint]], dict]:
    """
    Create a scoring strategy that weights checkpoints differently.
    
    Args:
        weights: List of weights for each checkpoint (should sum to 1.0)
    
    Returns:
        Scoring function
    """
    def scoring_strategy(checkpoints: List[Checkpoint]) -> dict:
        if not checkpoints:
            return {"total": 0, "result": 0}
        
        if len(weights) != len(checkpoints):
            # If weights don't match, use equal weights
            weights_normalized = [1.0 / len(checkpoints)] * len(checkpoints)
        else:
            # Normalize weights to sum to 1.0
            total_weight = sum(weights)
            weights_normalized = [w / total_weight for w in weights]
        
        total = sum(cp.total for cp in checkpoints)
        result = sum(
            (cp.result / cp.total) * cp.total * weight
            for cp, weight in zip(checkpoints, weights_normalized)
        )
        
        return {"total": total, "result": int(result)}
    
    return scoring_strategy


def time_penalized_scoring(max_time_seconds: float, penalty_factor: float = 0.1) -> Callable:
    """
    Create a scoring strategy that penalizes based on completion time.
    
    Args:
        max_time_seconds: Maximum expected time (no penalty if completed faster)
        penalty_factor: Penalty per unit of time over max (0.1 = 10% per unit)
    
    Returns:
        Scoring function that takes (checkpoints, elapsed_time)
    """
    def scoring_strategy(checkpoints: List[Checkpoint], elapsed_time: float) -> dict:
        base_total = sum(cp.total for cp in checkpoints)
        base_result = sum(cp.result for cp in checkpoints)
        
        # Calculate time penalty
        if elapsed_time > max_time_seconds:
            time_over = elapsed_time - max_time_seconds
            time_penalty = min(1.0, (time_over / max_time_seconds) * penalty_factor)
            adjusted_result = base_result * (1 - time_penalty)
        else:
            adjusted_result = base_result
        
        return {
            "total": base_total,
            "result": int(adjusted_result),
            "time_penalty": max(0, elapsed_time - max_time_seconds) if elapsed_time > max_time_seconds else 0,
        }
    
    return scoring_strategy


def efficiency_scoring(action_count: int, optimal_action_count: int) -> float:
    """
    Calculate efficiency score based on action count.
    
    Args:
        action_count: Number of actions the agent took
        optimal_action_count: Expected minimum number of actions
    
    Returns:
        Efficiency score (0.0 to 1.0)
    """
    if action_count <= optimal_action_count:
        return 1.0
    
    # Exponential decay: efficiency decreases as actions increase
    ratio = optimal_action_count / action_count
    return ratio


def composite_scoring(
    checkpoint_weight: float = 0.7,
    efficiency_weight: float = 0.2,
    time_weight: float = 0.1,
) -> Callable:
    """
    Create a composite scoring strategy combining multiple metrics.
    
    Args:
        checkpoint_weight: Weight for checkpoint-based score
        efficiency_weight: Weight for efficiency score
        time_weight: Weight for time-based score
    
    Returns:
        Scoring function
    """
    def scoring_strategy(
        checkpoints: List[Checkpoint],
        efficiency_score: float,
        elapsed_time: float,
        max_time: float,
    ) -> dict:
        # Normalize checkpoint score
        checkpoint_total = sum(cp.total for cp in checkpoints)
        checkpoint_result = sum(cp.result for cp in checkpoints)
        checkpoint_normalized = checkpoint_result / checkpoint_total if checkpoint_total > 0 else 0.0
        
        # Normalize time score (faster = better)
        time_normalized = max(0.0, 1.0 - (elapsed_time / max_time)) if max_time > 0 else 1.0
        
        # Composite score
        composite = (
            checkpoint_normalized * checkpoint_weight +
            efficiency_score * efficiency_weight +
            time_normalized * time_weight
        )
        
        # Scale to original checkpoint total
        final_result = int(composite * checkpoint_total)
        
        return {
            "total": checkpoint_total,
            "result": final_result,
            "breakdown": {
                "checkpoint_score": checkpoint_normalized,
                "efficiency_score": efficiency_score,
                "time_score": time_normalized,
                "composite_score": composite,
            }
        }
    
    return scoring_strategy


def quality_bonus_scoring(quality_score: float, bonus_factor: float = 0.1) -> Callable:
    """
    Add quality-based bonus to checkpoint scores.
    
    Args:
        quality_score: Quality metric (0.0 to 1.0)
        bonus_factor: Maximum bonus percentage (0.1 = 10% bonus)
    
    Returns:
        Scoring function
    """
    def scoring_strategy(checkpoints: List[Checkpoint]) -> dict:
        base_total = sum(cp.total for cp in checkpoints)
        base_result = sum(cp.result for cp in checkpoints)
        
        # Apply quality bonus
        bonus = base_result * quality_score * bonus_factor
        final_result = min(base_total, base_result + bonus)
        
        return {
            "total": base_total,
            "result": int(final_result),
            "quality_bonus": bonus,
        }
    
    return scoring_strategy

