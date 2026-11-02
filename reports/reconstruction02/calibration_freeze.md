# Calibration freeze — до evaluation, 02.11.2026

240 независимых calibration pairs; только complete negative определяют threshold. Frozen policy — frozen_policy.json; calibration raw data — ../examples/reconstruction02-calibration-v1.zip с checksum в calibration_archive.json. Eval directory на момент freeze отсутствовала.

Threshold: -4.20783885154492. Calibration FP: 12 / 240. Это empirical calibration, не гарантия FPR на новых условиях. Source IDs и scientific fingerprint сохранены. Code SHA данных — e2f0d08; source/runner/config/protocol fingerprint не менялся после development pilot. Изменения independent verifier/plotting не меняют научный метод.

Runtime calibration 296.9399484209998s,4 CPU workers. Полный verifier результатов PASS. Нельзя менять primary threshold/метод после этого commit и просмотра evaluation.
