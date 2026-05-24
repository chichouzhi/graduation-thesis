# Excalidraw Diagrams Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate 13 standalone Excalidraw files for the structural and flowchart placeholders in the graduation thesis text.

**Architecture:** A small Node.js generator builds Excalidraw element arrays from declarative diagram definitions. The generated files are written to the thesis workflow directory and verified by parsing JSON and checking required top-level keys.

**Tech Stack:** Node.js, Excalidraw JSON, Markdown README.

---

### Task 1: Create Generator

**Files:**
- Create: `scripts/generate-excalidraw-diagrams.js`

- [x] **Step 1: Define Excalidraw element helpers**

Create helper functions for rectangle nodes, text labels, arrows, section titles, and complete document assembly.

- [x] **Step 2: Define 13 diagram models**

Represent each figure with nodes, arrows, and labels matching the thesis placeholder descriptions.

- [x] **Step 3: Write generated files**

Create `毕设相关文件/毕设流程文件/excalidraw图表/`, write one `.excalidraw` file per diagram, and write `README.md`.

### Task 2: Verify Output

**Files:**
- Read: generated `.excalidraw` files

- [x] **Step 1: Parse every generated JSON file**

Run a Node verification script that loads each `.excalidraw` file with `JSON.parse`.

- [x] **Step 2: Check required top-level fields**

For each file, assert `type === "excalidraw"`, `version`, `source`, `elements`, `appState`, and `files` exist.

- [x] **Step 3: Check element IDs are unique**

For each file, compare element ID count against unique ID count.

