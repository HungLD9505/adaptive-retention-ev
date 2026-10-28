"""Verify declared Final matrix coverage and named scientific shortfalls."""

from __future__ import annotations

from experiments.hung_sprint2.dispatch_matched import require


def _coverage_status(coverage: dict, jobs: list[dict], planned: list[dict]) -> str:
    require(
        set(coverage)
        == {
            "selected_entities",
            "budgets",
            "seeds",
            "variants",
            "variant_categories",
            "replay_origins",
            "expected_jobs",
            "declared_shortfalls",
        },
        "Final coverage fields differ",
    )
    entities = coverage["selected_entities"]
    require(isinstance(entities, list) and entities, "Final cohort is empty")
    entity_keys = []
    for item in entities:
        require(set(item) == {"dataset_id", "city_id", "entity_id"}, "Final cohort fields differ")
        entity_keys.append((item["dataset_id"], item["city_id"], item["entity_id"]))
    require(entity_keys == sorted(set(entity_keys)), "Final cohort must be unique and sorted")
    budgets, seeds, variants = coverage["budgets"], coverage["seeds"], coverage["variants"]
    require(budgets == [7, 14, 28], "Final budgets must be 7/14/28")
    require(
        isinstance(seeds, list)
        and len(seeds) >= 3
        and seeds == sorted(set(seeds))
        and all(type(seed) is int and seed >= 0 for seed in seeds),
        "Final needs at least three sorted seeds",
    )
    require(
        isinstance(variants, list)
        and variants
        and variants == sorted(set(variants))
        and all(isinstance(value, str) and value for value in variants),
        "Final variants must be unique and sorted",
    )
    require(coverage["replay_origins"] == 90, "Locked Final replay must retain 90 origins")
    categories = coverage["variant_categories"]
    require(set(categories) == set(variants), "Final variant category map differs")
    required_baselines = {
        "seasonal_naive",
        "target_only",
        "frozen_source",
        "full_finetuning",
        "fixed_retention",
        "online_best_lambda",
        "source_error",
        "uncertainty",
        "drift",
    }
    required_ablations = {
        "without_confidence",
        "fixed_lambda",
        "parameter_retention",
        "different_block_size",
        "without_source_initialization",
    }
    all_categories = (
        {"main"}
        | {f"baseline:{name}" for name in required_baselines}
        | {f"ablation:{name}" for name in required_ablations}
    )
    for variant, labels in categories.items():
        require(
            isinstance(labels, list)
            and labels
            and len(labels) == len(set(labels))
            and set(labels) <= all_categories,
            f"Invalid Final category mapping for {variant}",
        )
    expected = {
        (*entity, budget, seed, variant)
        for entity in entity_keys
        for budget in budgets
        for seed in seeds
        for variant in variants
    }
    actual = {
        (
            job["dataset_id"],
            job["city_id"],
            job["entity_id"],
            job["budget_days"],
            job["seed"],
            job["variant"],
        )
        for job in jobs
    }
    require(
        len(actual) == len(jobs) and actual <= expected,
        "Final matrix has duplicate or unexpected cells",
    )
    require(
        coverage["expected_jobs"] == len(expected), "Final expected count differs from exact matrix"
    )
    for job, plan in zip(jobs, planned, strict=True):
        labels = categories[job["variant"]]
        for label in labels:
            if label.startswith("baseline:"):
                require(
                    job["method"] == label.split(":", 1)[1], "Final baseline alias/method differs"
                )
            elif label == "main":
                require(job["method"] == "confidence", "Final main method differs")
            elif label == "ablation:without_confidence":
                require(job["method"] == "without_confidence", "Final confidence ablation differs")
            elif label == "ablation:fixed_lambda":
                require(job["method"] == "fixed_retention", "Final fixed-lambda alias differs")
            elif label == "ablation:parameter_retention":
                require(
                    job["method"] == "confidence"
                    and plan["replay"].get("retention_kind") == "parameter",
                    "Final parameter ablation differs",
                )
            elif label == "ablation:different_block_size":
                require(
                    job["method"] == "confidence" and plan["replay"].get("block_days") != 14,
                    "Final block-size ablation differs",
                )
            elif label == "ablation:without_source_initialization":
                require(
                    job["method"] == "confidence"
                    and plan["target_init"] is not None
                    and plan["target_init"].get("initialization_kind") == "random_target",
                    "Final no-Source ablation differs",
                )
    labels_present = {label for job in jobs for label in categories[job["variant"]]}
    cities_present = {(job["dataset_id"], job["city_id"]) for job in jobs}
    required_cities = {("urbanev", "SZH")} | {
        ("charged", city) for city in ("MEL", "SZH", "AMS", "JHB", "SPO", "LOA")
    }
    shortfalls = coverage["declared_shortfalls"]
    require(
        isinstance(shortfalls, list)
        and all(isinstance(value, str) and value.strip() for value in shortfalls),
        "Final shortfall declarations are invalid",
    )
    incomplete = bool(
        expected - actual or all_categories - labels_present or required_cities - cities_present
    )
    require(not incomplete or bool(shortfalls), "Final coverage shortfall is undeclared")
    return "incomplete" if incomplete or shortfalls else "full"
