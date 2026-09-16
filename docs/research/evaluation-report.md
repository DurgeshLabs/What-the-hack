# Evaluation report: what the bundled model can and cannot claim

**Generated:** 2026-09-16 · **Dataset:** `ai/datasets/cleaned/cicids2017_archive_clean.csv`
**Tooling:** `ai/training/train_world_model.py`, `ai/evaluation/evaluate_models.py`

This is the honest evaluation the project needed before judging. Read it before anyone puts
an accuracy number on a slide.

## Headline

The world model, trained on the bundled replay, has **no discriminative signal**. It scores
a high F1 only because the test partition is almost entirely attack traffic. The simple
logistic-regression baseline ranks windows better than it does.

| Metric | Logistic baseline | World model |
| --- | --- | --- |
| F1 | 0.9147 | 0.9565 |
| ROC-AUC | 0.6717 | **0.2071** |
| PR-AUC | 0.9497 | 0.8792 |
| False-positive rate | 0.6667 | **1.0000** |
| True negatives | 2 of 6 | **0 of 6** |

Measured on a chronological split with a purge embargo, test fraction 0.5, 72 test windows,
threshold 0.5.

An ROC-AUC of 0.21 is worse than a coin flip. The confusion matrix shows why: the model
predicts attack for every window, so it catches every attack and every benign window too.
The F1 of 0.96 is an artefact of a test partition that is 92 percent attack.

**Do not quote the F1. If a judge asks for AUC, the current answer is 0.21.**

## Why the earlier result looked perfect

Two separate problems, both now fixed in the tooling.

**The model was trained on its own test data.** The training script used the entire CSV and
the evaluation script then scored the last twenty percent of it. The baseline was fit only
on the training portion, so the two were never comparable. Training now takes
`--test-fraction`, fits normalisation statistics on the training partition alone, and drops
`seq_len` windows at the boundary so no training sample can read across it. Evaluation
refuses a checkpoint whose recorded split does not match.

**The default split yields a single-class test set.** The bundled replay is ordered so that
its last 36 windows are one unbroken attack. At the default test fraction of 0.2 the entire
test partition is attack traffic, which makes precision, recall and F1 all exactly 1.0 and
leaves ROC-AUC and PR-AUC undefined. The evaluation script now detects this and prints a
caveat instead of a misleading score.

## The dataset is the binding constraint

| Property | Value |
| --- | --- |
| Total 60-second windows | 143 |
| Attack windows | 101 |
| Benign windows | 42 |
| Attack episodes | 6 |
| Longest episode | 36 windows, running to the end of the capture |

One hundred and four training windows is far too few to fit a two-layer LSTM over 37
features. The replay also carries a synthetic source-order timeline, because the archive
variant it came from omits capture timestamps, so its notion of "next minute" is not real
elapsed time. It is a demo fixture, not a benchmark.

## Early-warning metrics

Lead time is now measured rather than asserted, in `ai/evaluation/lead_time.py`. For each
attack episode it walks back through the benign windows immediately before onset while they
are already above the threshold, and reports that run as the warning.

| Metric | Logistic baseline | World model |
| --- | --- | --- |
| Episodes warned | 4 of 4 | 4 of 4 |
| Mean lead time | 60 s | 90 s |
| Maximum lead time | 180 s | 180 s |
| False warnings per hour | 40 | 60 |

These numbers are **not** usable evidence yet. A model that alarms on every window trivially
warns before every attack, so its lead time says nothing about skill. The metric itself is
tested against hand-built cases in `tests/ml/test_lead_time.py`; it is the model that needs
work, not the measurement.

## What has to happen before any accuracy claim

1. **Train on original timestamped CICIDS2017 files.** Real capture times, far more windows,
   and attack episodes distributed through the day rather than bunched at the end.
2. **Check the test partition has both classes** before reporting. The tooling now warns, but
   the fix is a better capture, not a different split.
3. **Fix the exposure gap.** The risk head trains on true feature vectors and is served on
   vectors the dynamics model predicted. Fine-tune it on rollouts.
4. **Calibrate and choose a threshold** against an agreed false-positive rate, rather than
   defaulting to 0.5.
5. **Report the baseline alongside the model, always.** Right now the baseline wins on
   ranking quality, and hiding that would be indefensible under questioning.

## Reproducing this

```bash
PYTHONPATH=.:backend python -m ai.training.train_world_model \
  ai/datasets/cleaned/cicids2017_archive_clean.csv --epochs 30 --test-fraction 0.5 --out /tmp/wm.pt

PYTHONPATH=.:backend python -m ai.evaluation.evaluate_models \
  ai/datasets/cleaned/cicids2017_archive_clean.csv /tmp/wm.pt --test-fraction 0.5
```

The bundled `ai/models/world_model.pt` is deliberately left in place. Its only job is to make
the dashboard show a plausible forecast for the demo, and it still does that. It is not the
artifact these numbers describe, and it is not evidence of accuracy.

## How to talk about this

> "We measure our forecaster against a logistic baseline on a chronological split with a
> purge embargo, and we report ROC-AUC and lead time, not just F1. On the compact replay we
> bundle for reproducibility, the neural forecaster does not yet beat the baseline, and we
> can show you exactly why: the capture is too small and its attacks are bunched at the end.
> That is a data problem we have diagnosed rather than a number we have hidden."

That answer is far stronger than a 100 percent F1 a judge can dismantle in one question.
