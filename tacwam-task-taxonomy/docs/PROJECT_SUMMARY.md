# TacWAM Task Taxonomy — Project Summary

## Goal

Maintain a clean, versioned registry of all TacWAM task definitions and understand **coverage across a two-level taxonomy** before releasing new collection batches.

This handoff deliberately excludes vendor-return QA for now.

## Current catalog

- Historical task-title records: **302**
- Normalized semantic keys: **297**
- Core L1 scenes: **7**
- Legacy/general L1 buckets: **2**
- L2 manipulation/contact families: **12**
- Source batches: Batch 2, Batch 3, Batch 4, Batch 5 Supplement, Batch 6

## Taxonomy definition

**L1 = scene.** The seven core scenes are Laboratory, Medical / First Aid, Workbench, Office, Kitchen, Bedroom, and Packing / Shipping. Two legacy buckets are retained for General / Teleop Alignment and General / Active Tactile tasks.

**L2 = the primary manipulation/contact family.** Each task currently receives one primary L2 assignment. If multi-label analysis is needed later, add secondary `skill_tags` without breaking the main L1 → L2 tree.

## What the website should answer

1. How many task definitions exist today?
2. How are they distributed across L1 scenes?
3. How are they distributed across L2 skills?
4. What does the L1 → L2 hierarchy look like interactively?
5. Which L1 × L2 cells are dense, sparse, or empty?
6. Which tasks belong to a selected scene or skill family?
7. Which source batch / PDF produced each task?

## Current coverage signal

Laboratory is the largest scene at **155 / 302** records. The least represented L2 families are **Measure / Label / Document (8)**, **Active Tactile / Press / Classify (8)**, and **Mix / Stir / Agitate (12)**.

These counts describe **task-definition coverage only**. They do not represent collected demo volume or qualified data volume.
