import contextvars
from fastapi import FastAPI, HTTPException
import datetime

session_request_timestamps: contextvars.ContextVar[list] = contextvars.ContextVar("session_request_timestamps", default=[])
session_token_counts: contextvars.ContextVar[list] = contextvars.ContextVar("session_token_counts", default=[])

app = FastAPI()

RPM_LIMIT = 60
TPM_LIMIT = 10000
WINDOW_SECONDS = 60


def is_rate_limited(tokens_used: int) -> bool:
    current_time = datetime.datetime.now()

    request_timestamps = session_request_timestamps.get()
    token_counts = session_token_counts.get()

    # Ensure lists are initialized if None (though default=[] should handle this)
    if request_timestamps is None:
        request_timestamps = []
    if token_counts is None:
        token_counts = []

    # Filter old timestamps and tokens
    valid_indices = [
        i for i, ts in enumerate(request_timestamps)
        if (current_time - ts).total_seconds() <= WINDOW_SECONDS
    ]
    request_timestamps = [request_timestamps[i] for i in valid_indices]
    token_counts = [token_counts[i] for i in valid_indices]

    # Check RPM
    if len(request_timestamps) + 1 > RPM_LIMIT:
        return True

    # Check TPM
    if sum(token_counts) + tokens_used > TPM_LIMIT:
        return True

    # If not rate-limited, add current request and update context variables
    request_timestamps.append(current_time)
    token_counts.append(tokens_used)

    session_request_timestamps.set(request_timestamps)
    session_token_counts.set(token_counts)

    return False


async def call_azure_o4_mini_model(prompt: str, tokens_to_simulate: int):
    if is_rate_limited(tokens_used=tokens_to_simulate):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later."
        )
    else:
        # Simulate a successful API call
        return {
            "response": f"Successfully processed prompt: '{prompt}' using {tokens_to_simulate} tokens.",
            "tokens_used": tokens_to_simulate
        }


@app.get("/")
async def root():
    return {"message": "Hello World"}
