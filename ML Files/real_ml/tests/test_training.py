import json
from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from train import FEATURES, check_split, evaluate, inputs, write_reports


def fixture():
    rows = []
    for day in (20191011, 20191012, 20191013, 20210318):
        for i, label in enumerate(("BIRD", "UAV")):
            row = dict.fromkeys(FEATURES, float(i))
            row.update(track_uid=f"{day}-{i}", recording_day=day, recording_session=str(day),
                       label=label, rcs_mean=None)
            rows.append(row)
    return pd.DataFrame(rows)


class TrainingTests(unittest.TestCase):
    def test_reproduction_and_reports(self):
        result = evaluate(fixture())
        self.assertEqual(result, evaluate(fixture().sample(frac=1, random_state=5)))
        with tempfile.TemporaryDirectory() as folder:
            write_reports(result, Path(folder))
            self.assertEqual(json.loads((Path(folder) / "evaluation.json").read_text())["final"], result["final"])
            self.assertTrue((Path(folder) / "confusion.png").read_bytes().startswith(b"\x89PNG"))

    def test_reject_corrupt_data(self):
        rows = fixture()
        for bad in (pd.concat([rows, rows]), rows.assign(label="UNKNOWN"),
                    rows.assign(veloX_std=float("inf")), rows[rows.label == "BIRD"]):
            with self.assertRaises(ValueError):
                evaluate(bad)
        with self.assertRaises(KeyError):
            evaluate(rows.drop(columns="rcs_std"))

    def test_overlap_and_prohibited_input(self):
        rows = fixture()
        with self.assertRaises(ValueError):
            check_split(rows, rows)
        with self.assertRaises(ValueError):
            inputs(rows, FEATURES + ["label"])
