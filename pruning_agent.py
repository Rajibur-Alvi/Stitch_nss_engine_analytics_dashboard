"""
pruning_agent.py — NSS Engine Pruning Agent
─────────────────────────────────────────────────────────────────────────────
Purpose
───────
Strip low-entropy "background noise" windows from a byte stream and output
only the high-entropy "signal patches" that carry real information.

Why this matters
────────────────
Most real-world files (logs, documents, mixed-script text, binary blobs) are
dominated by highly repetitive, low-entropy spans — padding, whitespace,
repeated headers, ASCII boilerplate.  Sending all of that to a downstream AI
model wastes compute and dilutes the signal.

The Pruning Agent solves this by:
  1. Using the Entropy Core's per-window Shannon entropy values.
  2. Computing a dynamic low-entropy cutoff from the file's own distribution
     (median or mean − margin) so the threshold adapts to every file.
  3. Keeping only windows above that cutoff — the "interesting" byte patches.
  4. Reporting exact data-reduction statistics to prove the 60-80% target.

Downstream AI contract
──────────────────────
The pruned output is a list of `SignalPatch` objects.  Each patch carries:
  • raw bytes        — the actual high-entropy byte window(s)
  • byte_offset      — position in the original file (for reconstruction)
  • entropy          — the Shannon entropy of this patch
  • is_spike         — whether the dynamic threshold flagged this as a spike

A downstream model therefore receives only the dense information, with full
provenance to reconstruct or re-anchor results back to the source file.
"""

from __future__ import annotations

import dataclasses
import math
from collections import Counter
from typing import TYPE_CHECKING

import numpy as np

# Shared constant from engine — one source of truth
WINDOW_SIZE = 16


@dataclasses.dataclass
class SignalPatch:
    """A single high-entropy patch extracted from the byte stream."""
    window_index: int           # Index in the original window sequence
    byte_offset:  int           # Byte position in the original file
    raw_bytes:    bytes         # The 16 (or fewer) bytes of this window
    entropy:      float         # Shannon entropy of this patch
    is_spike:     bool          # True if the dynamic threshold flagged it

    def to_dict(self) -> dict:
        return {
            "window_index": self.window_index,
            "byte_offset":  self.byte_offset,
            "entropy":      round(self.entropy, 4),
            "is_spike":     self.is_spike,
            "hex_preview":  self.raw_bytes[:8].hex(),          # first 8 bytes as hex
            "size_bytes":   len(self.raw_bytes),
        }


@dataclasses.dataclass
class PruningReport:
    """Complete statistics for one pruning run."""
    original_bytes:    int
    retained_bytes:    int
    pruned_bytes:      int
    original_windows:  int
    retained_windows:  int
    pruned_windows:    int
    reduction_pct:     float         # 0.0 – 100.0
    signal_patches:    list[SignalPatch]
    entropy_cutoff:    float          # the dynamic threshold used
    spike_patches:     int            # patches that are also spikes

    @property
    def target_met(self) -> bool:
        """True if we achieved ≥60 % data reduction."""
        return self.reduction_pct >= 60.0

    def to_dict(self) -> dict:
        return {
            "original_bytes":   self.original_bytes,
            "retained_bytes":   self.retained_bytes,
            "pruned_bytes":     self.pruned_bytes,
            "original_windows": self.original_windows,
            "retained_windows": self.retained_windows,
            "pruned_windows":   self.pruned_windows,
            "reduction_pct":    round(self.reduction_pct, 2),
            "entropy_cutoff":   round(self.entropy_cutoff, 4),
            "spike_patches":    self.spike_patches,
            "target_met":       self.target_met,
            "signal_patches":   [p.to_dict() for p in self.signal_patches[:100]],
        }


class PruningAgent:
    """
    Stateless agent that prunes a byte stream down to its high-entropy patches.

    Parameters
    ──────────
    cutoff_strategy : 'median'  — drop windows below the median entropy (default)
                      'mean'    — drop windows below the mean entropy
                      'percentile_N' — drop windows below the Nth percentile
                                       (e.g. 'percentile_40')
    merge_adjacent  : bool — merge neighbouring kept windows into contiguous
                             patches before returning (reduces patch count,
                             keeps context intact around transitions).
    """

    def __init__(
        self,
        cutoff_strategy: str  = "median",
        merge_adjacent:  bool = True,
    ):
        self.cutoff_strategy = cutoff_strategy
        self.merge_adjacent  = merge_adjacent

    # ── Cutoff computation ────────────────────────────────────────────

    def _compute_cutoff(self, entropy_series: list[float]) -> float:
        """Return the dynamic low-entropy cutoff for this file."""
        if not entropy_series:
            return 0.0
        arr = np.array(entropy_series)

        if self.cutoff_strategy == "mean":
            return float(arr.mean())

        if self.cutoff_strategy.startswith("percentile_"):
            pct = int(self.cutoff_strategy.split("_")[1])
            return float(np.percentile(arr, pct))

        # Default: median
        return float(np.median(arr))

    # ── Core pruning logic ────────────────────────────────────────────

    def prune(
        self,
        byte_data:      bytes,
        entropy_series: list[float],
        spike_indices:  list[int],
    ) -> PruningReport:
        """
        Run the full pruning pipeline.

        Steps
        ─────
        1. Compute the dynamic cutoff from the entropy distribution.
        2. Walk every 16-byte window; keep it if entropy ≥ cutoff.
           Spike windows are ALWAYS kept regardless of entropy value.
        3. Optionally merge adjacent kept windows into contiguous patches.
        4. Build and return a PruningReport with full statistics.

        Parameters
        ──────────
        byte_data      : original raw bytes (full file)
        entropy_series : per-window Shannon entropy from the Entropy Core
        spike_indices  : dynamic-threshold spike window indices
        """
        if not entropy_series:
            return PruningReport(
                original_bytes=len(byte_data), retained_bytes=0,
                pruned_bytes=len(byte_data), original_windows=0,
                retained_windows=0, pruned_windows=0,
                reduction_pct=100.0, signal_patches=[],
                entropy_cutoff=0.0, spike_patches=0,
            )

        cutoff      = self._compute_cutoff(entropy_series)
        spike_set   = set(spike_indices)
        kept_flags  = []                    # True = keep this window

        for i, e in enumerate(entropy_series):
            # Keep if: above cutoff OR is a spike (never discard spikes)
            keep = (e >= cutoff) or (i in spike_set)
            kept_flags.append(keep)

        # ── Merge adjacent kept windows into contiguous patches ───────
        if self.merge_adjacent:
            kept_flags = self._merge_adjacent(kept_flags)

        # ── Build SignalPatch objects ─────────────────────────────────
        signal_patches: list[SignalPatch] = []
        retained_bytes = 0

        for i, keep in enumerate(kept_flags):
            if not keep:
                continue
            start = i * WINDOW_SIZE
            end   = min(start + WINDOW_SIZE, len(byte_data))
            chunk = byte_data[start:end]
            retained_bytes += len(chunk)
            signal_patches.append(SignalPatch(
                window_index = i,
                byte_offset  = start,
                raw_bytes    = chunk,
                entropy      = entropy_series[i],
                is_spike     = (i in spike_set),
            ))

        original_bytes   = len(byte_data)
        pruned_bytes     = original_bytes - retained_bytes
        original_windows = len(entropy_series)
        retained_windows = sum(kept_flags)
        pruned_windows   = original_windows - retained_windows
        reduction_pct    = (pruned_bytes / original_bytes * 100) if original_bytes else 0.0

        return PruningReport(
            original_bytes   = original_bytes,
            retained_bytes   = retained_bytes,
            pruned_bytes     = pruned_bytes,
            original_windows = original_windows,
            retained_windows = retained_windows,
            pruned_windows   = pruned_windows,
            reduction_pct    = round(reduction_pct, 2),
            signal_patches   = signal_patches,
            entropy_cutoff   = cutoff,
            spike_patches    = sum(1 for p in signal_patches if p.is_spike),
        )

    # ── Merge helper ─────────────────────────────────────────────────

    @staticmethod
    def _merge_adjacent(flags: list[bool]) -> list[bool]:
        """
        Expand kept windows to include their immediate neighbours.
        This preserves one window of context on each side of a signal
        patch, which helps downstream models understand the transition
        boundary (e.g. the last few ASCII bytes before a Bengali block).
        """
        merged = list(flags)
        for i, keep in enumerate(flags):
            if keep:
                if i > 0:
                    merged[i - 1] = True        # left neighbour
                if i < len(flags) - 1:
                    merged[i + 1] = True        # right neighbour
        return merged
