#!/bin/bash
# Reproducible import of all existing evidence into data/store.db (idempotent).
set -e
cd /Users/danuzz/company-dataset
A=~/company-dataset-scratch-archive-2026-10-31
args=(--cache main=data/cache/validation.json)
for d in work work2 work3 v2_join v2_recruitee v2_teamtailor v2_personio v2_bamboohr run_workable run_workday run_bamboohr; do args+=(--cache "$d=$A/$d/cache/validation.json"); done
for f in $A/qa/*.jsonl; do args+=(--qa "qa_$(basename $f .jsonl)=$f"); done
for d in $A/work $A/work2 $A/work3; do [ -f $d/cache/pages.json ] && args+=(--pages $d/cache/pages.json); done
args+=(--pages data/cache/pages.json)
python -m company_dataset.store_import --db data/store.db --raw data/raw_2026-10-31 "${args[@]}" --report "$1"
