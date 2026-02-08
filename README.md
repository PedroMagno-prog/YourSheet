# Your_Sheet: Universal TTRPG Engine

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg) ![Flet](https://img.shields.io/badge/GUI-Flet-purple.svg) ![License](https://img.shields.io/badge/License-MIT-green.svg)

**Your_Sheet** is a system-agnostic RPG character manager designed to solve the "DM Pain" of managing complex, math-heavy game systems. Unlike standard digital sheets, it features a **programmable logic engine** that allows users to define conditional triggers (e.g., "Explode dice on 6", "Reroll 1s") dynamically.

## 🎯 Key Features

### 🎲 Advanced Dice Parser (`dice_engine.py`)
Instead of simple random number generation, I engineered a custom parser using **Regex** to interpret complex RPG formulas.
- **Supports:** Standard notation (`4d6`), Modifiers (`+5`), Drop Lowest/Highest (`dl1`, `dh1`), and Exploding Dice (`e6`).
- **Context-Aware:** Parses variables directly from the character sheet (e.g., parsing `1d20 + str_mod`).

### ⚡ Conditional Logic System
The core differentiator of this project is the **Trigger & Effect System**. Rules are not hardcoded; they are objects that can be attached to specific actions.
- **Triggers:** Define activation conditions (e.g., `trigger_val == 20`).
- **Scopes:** Apply to `any` die in the pool or just the `first` one.
- **Effects:** Dynamic outcome modification (`reroll`, `add_bonus`, `explode`).

### 🏗️ Modular Architecture
- **JSON-Based Persistence:** All character data and global rules are stored in a hierarchical JSON structure (`rpg_data.json`), making the system portable and easy to integrate with other tools.
- **Reactive UI:** Built with **Flet** (Flutter for Python) to ensure real-time updates and a responsive cross-platform interface.

## 🛠️ Code Highlight: The Logic Engine

The `DiceEngine` class handles the probability complexity. Here is how it processes custom rules before the final output:

```python
# From dice_engine.py
def apply_custom_rules(self, rolagens: list, sides: int, active_rules: list):
    """
    Iterates through dice results to apply logic gates (Reroll, Explode, Add).
    Separates the 'mechanical' roll from the 'rule' layer.
    """
    for rule in active_rules:
        if rule["effect"] == "reroll":
            # Replaces the value based on trigger
            new_val = self._roll_single_die(sides)
            rolagens[i] = new_val
        elif rule["effect"] == "explode":
             # Adds new dice to the pool recursively
            extra = self._roll_single_die(sides)
            bonus_total += extra
