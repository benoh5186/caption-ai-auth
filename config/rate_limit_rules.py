RATE_LIMIT_RULES = {
    "/api/v1/auth": {
        "/signup": {
            "type": "token_bucket",
            "max_tokens": 2,
            "refill_rate": 2 / 60,
            "window_seconds": 60,
        },
        "/login": {
            "type": "token_bucket",
            "max_tokens": 6,
            "refill_rate": 6 / 60,
            "window_seconds": 60,
        },
    },
    "/api/v1/session": {
        "/load-sessions": {
            "type": "token_bucket",
            "max_tokens": 10,
            "refill_rate": 10 / 30,
            "window_seconds": 30,
        },
        "/load-session/{session_id}": {
            "type": "token_bucket",
            "max_tokens": 10,
            "refill_rate": 10 / 30,
            "window_seconds": 30,
        },
        "/load-session-video/{session_id}": {
            "type": "token_bucket",
            "max_tokens": 20,
            "refill_rate": 20 / 60,
            "window_seconds": 60,
        },
        "/create-session": {
            "type": "token_bucket",
            "max_tokens": 1,
            "refill_rate": 1 / 5,
            "window_seconds": 5,
        },
        "/delete-session/{session_id}": {
            "type": "token_bucket",
            "max_tokens": 2,
            "refill_rate": 2 / 5,
            "window_seconds": 5,
        },
        "/save-session/{session_id}": {
            "type": "token_bucket",
            "max_tokens": 10,
            "refill_rate": 10 / 60,
            "window_seconds": 60,
        },
        "/upload-video/{session_id}": {
            "type": "token_bucket",
            "max_tokens": 5,
            "refill_rate": 5 / 30,
            "window_seconds": 30,
        },
    },
    "/api/v1/transcribe": {
        "/transcribe/{session_id}": {
            "type": "token_bucket",
            "max_tokens": 5,
            "refill_rate": 5 / 60,
            "window_seconds": 60,
        },
        "/export/{session_id}": {
            "type": "token_bucket",
            "max_tokens": 10,
            "refill_rate": 10 / 60,
            "window_seconds": 60,
        },
        "/export-status/{job_id}/{session_id}": {
            "type": "token_bucket",
            "max_tokens": 10,
            "refill_rate": 10 / 60,
            "window_seconds": 60,
        },
        "/download/{job_id}": {
            "type": "token_bucket",
            "max_tokens": 10,
            "refill_rate": 10 / 60,
            "window_seconds": 60,
        },
        "/transcript/{session_id}": {
            "type": "token_bucket",
            "max_tokens": 2,
            "refill_rate": 2 / 60,
            "window_seconds": 60,
        },
    },
}
