"""Offline NRC track classification. Fixed protocol, no model export."""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier, export_text

from download_data import REVISION
from preprocess import BASE

LABELS = ["BIRD", "UAV"]
FEATURES = [f"{field}_{stat}" for field in ("veloX", "veloY", "veloZ", "rcs")
            for stat in ("mean", "std")]
CUTOFF = 20201218
SEED = 20


def inputs(rows, features):
    if list(features) != FEATURES:
        raise ValueError("Expected the frozen measurement allowlist")
    values = rows[features].apply(pd.to_numeric, errors="raise")
    if np.isinf(values).any().any():
        raise ValueError("Infinite measurement")
    return values


def check_split(train, test):
    for key in ("track_uid", "recording_session", "recording_day"):
        if set(train[key]) & set(test[key]):
            raise ValueError(f"Overlapping {key}")
    if set(train.label) != set(LABELS) or test.empty:
        raise ValueError("Insufficient training or evaluation support")


def scores(y, predicted):
    report = classification_report(y, predicted, labels=LABELS, output_dict=True, zero_division=0)
    return dict(classes={key: report[key] for key in LABELS},
                accuracy=accuracy_score(y, predicted),
                balanced_accuracy=np.mean([report[k]["recall"] for k in LABELS]) if len(set(y)) == 2 else None,
                macro_f1=report["macro avg"]["f1-score"],
                confusion=confusion_matrix(y, predicted, labels=LABELS).tolist())


def evaluate(rows):
    keys = ["track_uid", "recording_session", "recording_day", "label"]
    if rows[keys].isna().any().any() or rows.track_uid.duplicated().any():
        raise ValueError("Missing identity or duplicate track")
    if not set(rows.label) <= {*LABELS, "HUMAN", "VEHICLE"}:
        raise ValueError("Unexpected class")
    rows = rows[rows.label.isin(LABELS)].sort_values("track_uid")
    x = inputs(rows, FEATURES)
    dev = rows[rows.recording_day < CUTOFF]
    final = rows[rows.recording_day >= CUTOFF]
    check_split(dev, final)
    if set(final.label) != set(LABELS) or dev.recording_day.nunique() < 3:
        raise ValueError("Insufficient independent class coverage")

    candidates = {
        "Majority": DummyClassifier(strategy="most_frequent"),
        "Logistic": LogisticRegression(class_weight="balanced", random_state=SEED),
        "Shallow tree": DecisionTreeClassifier(max_depth=3, min_samples_leaf=10,
                                              class_weight="balanced", random_state=SEED),
    }
    models = {name: make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True),
                                  StandardScaler(), model) for name, model in candidates.items()}
    development = {}
    by_day = {}
    for name, model in models.items():
        predictions = pd.Series(index=dev.index, dtype=object)
        by_day[name] = {}
        for day, validation in dev.groupby("recording_day"):
            training = dev[dev.recording_day != day]
            check_split(training, validation)
            fit = clone(model).fit(x.loc[training.index], training.label)
            pred = fit.predict(x.loc[validation.index])
            predictions.loc[validation.index] = pred
            by_day[name][str(day)] = scores(validation.label, pred)
        development[name] = scores(dev.label, predictions)
    # Exact ties favor the earlier, simpler candidate. Reference is eligible.
    selected = max(models, key=lambda name: development[name]["balanced_accuracy"])
    holdout = {}
    final_days = {}
    explanation = {}
    for name, model in models.items():
        model.fit(x.loc[dev.index], dev.label)
        pred = pd.Series(model.predict(x.loc[final.index]), index=final.index)
        holdout[name] = scores(final.label, pred)
        final_days[name] = {str(day): scores(group.label, pred.loc[group.index])
                            for day, group in final.groupby("recording_day")}
        if name == selected:
            estimator = model.steps[-1][1]
            if name == "Logistic":
                explanation = dict(zip(FEATURES, estimator.coef_[0]))
            elif name == "Shallow tree":
                explanation = {"standardized_tree": export_text(estimator, feature_names=FEATURES)}
    return dict(features=FEATURES, cutoff=CUTOFF, seed=SEED, labels=LABELS, selected=selected,
                development=development, development_days=by_day, final=holdout,
                final_days=final_days, explanation=explanation,
                configurations={k: v.get_params() for k, v in candidates.items()})


def write_reports(result, directory):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "evaluation.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.4), layout="constrained")
    for ax, (name, metrics) in zip(axes, result["final"].items()):
        matrix = np.array(metrics["confusion"])
        ax.imshow(matrix, cmap="Blues", vmin=0, vmax=sum(map(sum, matrix)))
        for (i, j), n in np.ndenumerate(matrix):
            ax.text(j, i, str(n), ha="center", va="center",
                    color="white" if n > matrix.sum() / 2 else "black")
        ax.set(xticks=[0, 1], yticks=[0, 1], xticklabels=LABELS, yticklabels=LABELS,
               xlabel="Predicted class", title=name)
    axes[0].set_ylabel("Recorded class")
    fig.suptitle("Later recording days · number of completed tracks")
    fig.savefig(directory / "confusion.png", dpi=180)
    plt.close(fig)
    values = pd.DataFrame({stage: {name: item["balanced_accuracy"] for name, item in
                                   result[stage].items()} for stage in ("development", "final")})
    ax = values.plot.bar(rot=0, ylim=(0, 1), ylabel="Balanced accuracy",
                         color=["#54728c", "#ce782a"], title="Earlier-day validation and later-day holdout")
    ax.figure.tight_layout()
    ax.figure.savefig(directory / "comparison.png", dpi=180)
    plt.close(ax.figure)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tracks", type=Path, default=BASE / "data/processed/tracks.csv")
    parser.add_argument("--output", type=Path, default=BASE / "reports/phase2")
    args = parser.parse_args()
    tracks = pd.read_csv(args.tracks)
    result = evaluate(tracks)
    result.update(dataset_revision=REVISION, tracks_sha256=hashlib.sha256(args.tracks.read_bytes()).hexdigest(),
                  day_counts=pd.crosstab(tracks.recording_day, tracks.label).to_dict(orient="index"))
    write_reports(result, args.output)
