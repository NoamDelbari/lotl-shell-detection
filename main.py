"""
main.py -- single entry point for the detection pipeline.

Examples
--------
    # 5-fold CV for one model on one dataset
    python main.py cv --model xgboost --dataset dataset1

    # train on train split, evaluate on test split, per-source breakdown
    python main.py holdout --model cnn1d --dataset dataset2

    # every model x every dataset, holdout metrics -> results/summary.json
    python main.py all

    # cross-dataset transfer for one model (train D1 -> test D2)
    python main.py transfer --model xgboost --train dataset1 --test dataset2

The command dispatch is the only place that enumerates datasets/models; the
`src` package underneath is entirely dataset-agnostic (Dataset Dependency Rule).
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from src import ingestion
from src.evaluation import (cross_validate, evaluate_holdout, compute_metrics,
                            per_source_breakdown)
from src.models import MODEL_BUILDERS, MODEL_OWNER, build_model

RESULTS = Path(__file__).resolve().parent / "results"
RESULTS.mkdir(exist_ok=True)


def _xy(df):
    return df["command"].to_numpy(), df["label"].to_numpy()


def cmd_cv(args):
    train, _ = ingestion.load(args.dataset)
    X, y = _xy(train)
    t0 = time.time()
    res = cross_validate(lambda: build_model(args.model), X, y,
                         n_splits=args.folds)
    res["model"], res["dataset"] = args.model, args.dataset
    res["seconds"] = round(time.time() - t0, 1)
    _dump(f"cv_{args.model}_{args.dataset}.json", res)
    s = res["summary"]
    print(f"[cv] {args.model} on {args.dataset} ({args.folds}-fold, "
          f"{res['seconds']}s): "
          f"F1={s['f1']['mean']:.4f}+/-{s['f1']['std']:.4f}  "
          f"ROC-AUC={s['roc_auc']['mean']:.4f}  "
          f"Recall={s['recall']['mean']:.4f}  FPR={s['fpr']['mean']:.4f}")


def cmd_holdout(args):
    train, test = ingestion.load(args.dataset)
    Xtr, ytr = _xy(train)
    Xte, yte = _xy(test)
    model = build_model(args.model)
    t0 = time.time()
    metrics = evaluate_holdout(model, Xtr, ytr, Xte, yte)
    seconds = round(time.time() - t0, 1)
    by_source = per_source_breakdown(model, Xte, yte, test["source"].to_numpy())
    out = {"model": args.model, "dataset": args.dataset, "seconds": seconds,
           "metrics": metrics, "per_source": by_source}
    _dump(f"holdout_{args.model}_{args.dataset}.json", out)
    print(f"[holdout] {args.model} on {args.dataset} ({seconds}s): "
          f"F1={metrics['f1']:.4f}  P={metrics['precision']:.4f}  "
          f"R={metrics['recall']:.4f}  ROC-AUC={metrics['roc_auc']:.4f}  "
          f"FPR={metrics['fpr']:.4f}")


def cmd_transfer(args):
    train, _ = ingestion.load(args.train)
    _, test = ingestion.load(args.test)   # test on the OTHER dataset's test split
    Xtr, ytr = _xy(train)
    Xte, yte = _xy(test)
    model = build_model(args.model)
    metrics = evaluate_holdout(model, Xtr, ytr, Xte, yte)
    out = {"model": args.model, "train": args.train, "test": args.test,
           "metrics": metrics}
    _dump(f"transfer_{args.model}_{args.train}_to_{args.test}.json", out)
    print(f"[transfer] {args.model}: train {args.train} -> test {args.test}: "
          f"F1={metrics['f1']:.4f}  ROC-AUC={metrics['roc_auc']:.4f}  "
          f"Recall={metrics['recall']:.4f}")


def cmd_all(args):
    summary = {}
    for ds in ingestion.available_datasets():
        for model_name in MODEL_BUILDERS:
            train, test = ingestion.load(ds)
            Xtr, ytr = _xy(train)
            Xte, yte = _xy(test)
            model = build_model(model_name)
            metrics = evaluate_holdout(model, Xtr, ytr, Xte, yte)
            summary.setdefault(ds, {})[model_name] = metrics
            print(f"  {ds:9s} {model_name:16s} "
                  f"F1={metrics['f1']:.4f} ROC-AUC={metrics['roc_auc']:.4f} "
                  f"FPR={metrics['fpr']:.4f}")
    _dump("summary.json", summary)


def _dump(name, obj):
    (RESULTS / name).write_text(json.dumps(obj, indent=2))


def build_parser():
    p = argparse.ArgumentParser(description="LotL shell-command detection pipeline")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("cv", help="stratified k-fold CV")
    c.add_argument("--model", required=True, choices=sorted(MODEL_BUILDERS))
    c.add_argument("--dataset", required=True, choices=ingestion.available_datasets())
    c.add_argument("--folds", type=int, default=5)
    c.set_defaults(func=cmd_cv)

    c = sub.add_parser("holdout", help="train split -> test split")
    c.add_argument("--model", required=True, choices=sorted(MODEL_BUILDERS))
    c.add_argument("--dataset", required=True, choices=ingestion.available_datasets())
    c.set_defaults(func=cmd_holdout)

    c = sub.add_parser("transfer", help="train on one dataset, test on another")
    c.add_argument("--model", required=True, choices=sorted(MODEL_BUILDERS))
    c.add_argument("--train", required=True, choices=ingestion.available_datasets())
    c.add_argument("--test", required=True, choices=ingestion.available_datasets())
    c.set_defaults(func=cmd_transfer)

    c = sub.add_parser("all", help="every model x every dataset (holdout)")
    c.set_defaults(func=cmd_all)
    return p


if __name__ == "__main__":
    args = build_parser().parse_args()
    args.func(args)
