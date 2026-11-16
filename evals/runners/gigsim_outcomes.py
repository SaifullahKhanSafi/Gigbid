from evals.runners.common import save


def run():
    # Fail explicitly rather than inventing a simulator outcome or using local fixed replies.
    return save(
        "official_outcomes",
        {
            "status": "blocked_missing_official_service",
            "reply_rate": None,
            "hire_rate": None,
            "hidden_test": None,
            "reason": "Instructor GigSim URL, specification, dev client preferences and hidden runner were not supplied.",
        },
    )


if __name__ == "__main__":
    run()
