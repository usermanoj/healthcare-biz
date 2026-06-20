"""Create Phase 3 risk and claim model notebooks."""

from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = PROJECT_ROOT / "notebooks"


def markdown_cell(source: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": source.strip().splitlines(keepends=True),
    }


def code_cell(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.strip().splitlines(keepends=True),
    }


def base_setup_cells(task: str) -> list[dict]:
    title = "Visit Risk Classification" if task == "risk" else "Claim Outcome Classification"
    target = "risk_score" if task == "risk" else "claim_status"
    metrics_file = f"{task}_model_metrics.json"
    feature_file = f"{task}_feature_set.json"
    return [
        markdown_cell(
            f"""
            # Phase 3 - {title}

            **Target variable:** `{target}`

            This notebook documents the Phase 3 model-development workflow:
            leakage-aware features, time-based split, Logistic Regression
            baseline, Random Forest advanced model, class imbalance handling,
            saved artifacts, and model-selection results.
            """
        ),
        code_cell(
            f"""
            from pathlib import Path
            import json
            import pandas as pd

            PROJECT_ROOT = Path.cwd()
            if PROJECT_ROOT.name == "notebooks":
                PROJECT_ROOT = PROJECT_ROOT.parent

            PHASE3_DIR = PROJECT_ROOT / "data_outputs" / "phase3"
            MODEL_TABLE_PATH = PROJECT_ROOT / "data_outputs" / "model_table.csv"
            METRICS_PATH = PHASE3_DIR / "{metrics_file}"
            FEATURE_SET_PATH = PHASE3_DIR / "{feature_file}"

            metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
            feature_set = json.loads(FEATURE_SET_PATH.read_text(encoding="utf-8"))
            model_table = pd.read_csv(MODEL_TABLE_PATH)
            """
        ),
        markdown_cell("## 1. Business Purpose and Target Definition"),
        code_cell(
            """
            print(metrics["business_purpose"])
            print("Target:", metrics["target"])
            print("Labels:", metrics["labels"])
            """
        ),
        markdown_cell("## 2. Feature Set and Leakage Controls"),
        code_cell(
            """
            print("Categorical features")
            display(pd.Series(feature_set["categorical_features"], name="feature"))

            print("Numeric features")
            display(pd.Series(feature_set["numeric_features"], name="feature"))

            print("Leakage exclusions")
            display(pd.Series(feature_set["leakage_exclusions"], name="excluded_column"))
            """
        ),
        code_cell(
            """
            pd.DataFrame(
                [
                    {"feature_group": group, "justification": reason}
                    for group, reason in feature_set["feature_justification"].items()
                ]
            )
            """
        ),
        markdown_cell("## 3. Time-Based Split"),
        code_cell(
            """
            metrics["split"]
            """
        ),
        markdown_cell("## 4. Class Imbalance Analysis"),
        code_cell(
            """
            pd.DataFrame(metrics["class_distribution"]["train"]).T
            """
        ),
        code_cell(
            """
            metrics["imbalance_strategy"]
            """
        ),
        markdown_cell("## 5. Baseline Model - Logistic Regression"),
        code_cell(
            """
            baseline = metrics["baseline_logistic_regression"]
            pd.DataFrame(
                [
                    {"split": "train", **baseline["train_metrics"]},
                    {"split": "test", **baseline["test_metrics"]},
                ]
            )[["split", "accuracy", "balanced_accuracy", "macro_f1", "weighted_f1", "business_recall"]]
            """
        ),
        code_cell(
            f"""
            pd.read_csv(PHASE3_DIR / "{task}_baseline_confusion_matrix_test.csv", index_col=0)
            """
        ),
        markdown_cell("## 6. Advanced Model - Random Forest"),
        code_cell(
            """
            advanced = metrics["advanced_random_forest"]
            print("Best parameters:", advanced["best_params"])
            pd.DataFrame(advanced["tuning_results"])
            """
        ),
        code_cell(
            """
            pd.DataFrame(
                [
                    {"split": "train", **advanced["train_metrics"]},
                    {"split": "test", **advanced["test_metrics"]},
                ]
            )[["split", "accuracy", "balanced_accuracy", "macro_f1", "weighted_f1", "business_recall"]]
            """
        ),
        code_cell(
            f"""
            pd.read_csv(PHASE3_DIR / "{task}_advanced_confusion_matrix_test.csv", index_col=0)
            """
        ),
        markdown_cell("## 7. Feature Importance"),
        code_cell(
            f"""
            pd.read_csv(PHASE3_DIR / "{task}_random_forest_feature_importance.csv").head(20)
            """
        ),
        markdown_cell("## 8. Selected Model Artifact"),
        code_cell(
            """
            metrics["selected_model"]
            """
        ),
    ]


def write_notebook(path: Path, cells: list[dict]) -> None:
    nb = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.12",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    path.write_text(json.dumps(nb, indent=2), encoding="utf-8")


def main() -> None:
    NOTEBOOK_DIR.mkdir(parents=True, exist_ok=True)
    write_notebook(NOTEBOOK_DIR / "02_risk_model.ipynb", base_setup_cells("risk"))
    write_notebook(NOTEBOOK_DIR / "03_claim_model.ipynb", base_setup_cells("claim"))
    print(f"Wrote notebooks under {NOTEBOOK_DIR}")


if __name__ == "__main__":
    main()
