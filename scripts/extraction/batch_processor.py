"""
Batch Processor for Incremental Extraction

Handles batch processing of extraction tasks with checkpoint saving,
resume capability, and progress tracking.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Callable
from tqdm import tqdm
import time


class BatchProcessor:
    """Process items in batches with checkpointing and progress tracking."""
    
    def __init__(
        self,
        batch_size: int = 5,
        checkpoint_dir: str = "data/checkpoints",
        output_file: str = None,
        task_name: str = "extraction"
    ):
        """
        Initialize batch processor.
        
        Args:
            batch_size: Number of items per batch
            checkpoint_dir: Directory to save checkpoints
            output_file: Final output file path
            task_name: Name of task for checkpoint files
        """
        self.batch_size = batch_size
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.output_file = output_file
        self.task_name = task_name
        
        self.results = []
        self.errors = []
        self.processed_indices = set()
    
    def process(
        self,
        items: List[Any],
        process_func: Callable,
        resume: bool = True
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Process items in batches with checkpointing.
        
        Args:
            items: List of items to process
            process_func: Function to process each batch, returns list of results
            resume: If True, resume from last checkpoint
            
        Returns:
            Tuple of (results, errors)
        """
        # Check for existing progress
        if resume:
            self._load_checkpoint()
        
        # Calculate batches
        total_batches = (len(items) + self.batch_size - 1) // self.batch_size
        
        print(f"Processing {len(items)} items in {total_batches} batches of {self.batch_size}")
        
        if self.processed_indices:
            print(f"Resuming: {len(self.processed_indices)} items already processed")
        
        # Process batches
        with tqdm(total=len(items), initial=len(self.processed_indices)) as pbar:
            for batch_idx in range(0, len(items), self.batch_size):
                # Skip if already processed
                if batch_idx in self.processed_indices:
                    pbar.update(min(self.batch_size, len(items) - batch_idx))
                    continue
                
                # Get batch
                batch_end = min(batch_idx + self.batch_size, len(items))
                batch = items[batch_idx:batch_end]
                
                # Process batch
                try:
                    batch_results = process_func(batch)
                    
                    # Validate results
                    if not isinstance(batch_results, list):
                        raise ValueError(f"process_func must return list, got {type(batch_results)}")
                    
                    # Add to results
                    self.results.extend(batch_results)
                    self.processed_indices.add(batch_idx)
                    
                    # Save checkpoint
                    self._save_checkpoint(batch_idx, batch_results)
                    
                    pbar.update(len(batch))
                    
                except Exception as e:
                    error_info = {
                        'batch_idx': batch_idx,
                        'batch_size': len(batch),
                        'error': str(e),
                        'items': batch[:2] if len(batch) > 2 else batch  # First 2 items for context
                    }
                    self.errors.append(error_info)
                    print(f"\n✗ Error processing batch {batch_idx}: {e}")
                    
                    # Continue or stop based on error severity
                    # For now, continue processing remaining batches
                    pbar.update(len(batch))
                
                # Small delay to avoid rate limits
                time.sleep(0.5)
        
        # Save final results
        if self.output_file:
            self._save_final_results()
        
        # Generate report
        self._generate_report()
        
        return self.results, self.errors
    
    def _save_checkpoint(self, batch_idx: int, batch_results: List[Dict[str, Any]]):
        """Save checkpoint after processing a batch."""
        checkpoint_file = self.checkpoint_dir / f"{self.task_name}_batch_{batch_idx}.json"
        
        checkpoint_data = {
            'batch_idx': batch_idx,
            'batch_size': len(batch_results),
            'results': batch_results,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
    
    def _load_checkpoint(self):
        """Load existing checkpoints to resume processing."""
        checkpoint_files = list(self.checkpoint_dir.glob(f"{self.task_name}_batch_*.json"))
        
        for checkpoint_file in checkpoint_files:
            try:
                with open(checkpoint_file, 'r') as f:
                    checkpoint_data = json.load(f)
                
                batch_idx = checkpoint_data['batch_idx']
                batch_results = checkpoint_data['results']
                
                self.results.extend(batch_results)
                self.processed_indices.add(batch_idx)
                
            except Exception as e:
                print(f"Warning: Failed to load checkpoint {checkpoint_file}: {e}")
    
    def _save_final_results(self):
        """Save final aggregated results."""
        output_path = Path(self.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n✓ Final results saved to {self.output_file}")
    
    def _generate_report(self):
        """Generate extraction report."""
        report = {
            'task': self.task_name,
            'total_items': len(self.results),
            'total_batches': len(self.processed_indices),
            'successful': len(self.results),
            'errors': len(self.errors),
            'error_details': self.errors
        }
        
        report_file = self.checkpoint_dir / f"{self.task_name}_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print("\n" + "="*60)
        print("EXTRACTION REPORT")
        print("="*60)
        print(f"Task: {self.task_name}")
        print(f"Total items processed: {len(self.results)}")
        print(f"Successful: {len(self.results)}")
        print(f"Errors: {len(self.errors)}")
        
        if self.errors:
            print("\nErrors encountered:")
            for error in self.errors:
                print(f"  Batch {error['batch_idx']}: {error['error']}")
        
        print(f"\nReport saved to {report_file}")


def batch_process_with_retry(
    items: List[Any],
    process_func: Callable,
    batch_size: int = 5,
    max_retries: int = 3,
    **kwargs
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Convenience function for batch processing with automatic retry.
    
    Args:
        items: Items to process
        process_func: Processing function
        batch_size: Batch size
        max_retries: Max retry attempts for failed batches
        **kwargs: Additional args for BatchProcessor
        
    Returns:
        Tuple of (results, errors)
    """
    processor = BatchProcessor(batch_size=batch_size, **kwargs)
    
    results, errors = processor.process(items, process_func)
    
    # Retry failed batches with smaller batch size
    if errors and max_retries > 0:
        print(f"\nRetrying {len(errors)} failed batches with smaller batch size...")
        
        # Collect failed items
        failed_items = []
        for error in errors:
            failed_items.extend(error.get('items', []))
        
        if failed_items:
            retry_processor = BatchProcessor(
                batch_size=max(1, batch_size // 2),
                **kwargs
            )
            
            retry_results, retry_errors = retry_processor.process(
                failed_items,
                process_func,
                resume=False
            )
            
            results.extend(retry_results)
            errors = retry_errors
    
    return results, errors


# Export
__all__ = ['BatchProcessor', 'batch_process_with_retry']
