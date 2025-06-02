import pytest
import asyncio
import datetime
import time

# Items to import from main.py
from main import (
    is_rate_limited,
    session_request_timestamps,
    session_token_counts,
    RPM_LIMIT,
    TPM_LIMIT,
    WINDOW_SECONDS
)

# Helper function to reset context variables for isolation
def reset_context_vars():
    session_request_timestamps.set([])
    session_token_counts.set([])

@pytest.fixture(autouse=True)
def auto_reset_context_vars():
    """Ensure context vars are reset before each test."""
    reset_context_vars()

# Test 1: Single request within limits
def test_single_request_within_limits():
    assert not is_rate_limited(tokens_used=100)
    assert len(session_request_timestamps.get()) == 1
    assert session_token_counts.get() == [100]

# Test 2: Multiple requests within RPM/TPM limits
def test_multiple_requests_within_rpm_tpm_limits():
    for _ in range(5):
        assert not is_rate_limited(tokens_used=1000)
    assert len(session_request_timestamps.get()) == 5
    assert session_token_counts.get() == [1000] * 5

# Test 3: Exceed RPM limit
def test_exceed_rpm_limit():
    # Fill up to RPM_LIMIT - 1 requests
    for _ in range(RPM_LIMIT -1): # Corrected to RPM_LIMIT -1 to make space for one more
        assert not is_rate_limited(tokens_used=10)
    
    # The RPM_LIMIT-th request should also pass
    assert not is_rate_limited(tokens_used=10) 
    assert len(session_request_timestamps.get()) == RPM_LIMIT

    # The (RPM_LIMIT + 1)-th request should fail
    assert is_rate_limited(tokens_used=10)

# Test 4: Exceed TPM limit
def test_exceed_tpm_limit():
    # Use a large chunk of tokens, but stay under the limit
    assert not is_rate_limited(tokens_used=TPM_LIMIT - 100)
    assert len(session_request_timestamps.get()) == 1
    assert session_token_counts.get() == [TPM_LIMIT - 100]

    # This request should exceed the TPM limit
    assert is_rate_limited(tokens_used=101) 
     # Verify that the lists were not modified by the rate-limited call
    assert len(session_request_timestamps.get()) == 1 
    assert session_token_counts.get() == [TPM_LIMIT - 100]


# Test 5: Window reset
def test_window_reset():
    # Initial call
    assert not is_rate_limited(tokens_used=10)
    assert len(session_request_timestamps.get()) == 1
    first_timestamp = session_request_timestamps.get()[0]
    
    # Manually age the timestamp in the context variable
    # Get current lists (copies)
    current_timestamps = session_request_timestamps.get().copy()
    current_tokens = session_token_counts.get().copy()

    # Modify the timestamp of the first (and only) request
    current_timestamps[0] = first_timestamp - datetime.timedelta(seconds=WINDOW_SECONDS + 5)
    
    # Set the modified lists back to the context
    session_request_timestamps.set(current_timestamps)
    session_token_counts.set(current_tokens) # token count for the aged request remains

    # This call should see the old request as expired
    assert not is_rate_limited(tokens_used=20)
    # The lists should now contain only the second request's data
    assert len(session_request_timestamps.get()) == 1
    assert session_token_counts.get() == [20]
    new_timestamp = session_request_timestamps.get()[0]
    # Check that the new timestamp is recent (not the aged one)
    assert (datetime.datetime.now() - new_timestamp).total_seconds() < 5


# Test 6: Concurrent sessions simulation
def test_concurrent_sessions_simulation():
    # --- Session 1 Setup ---
    # Context is already clean due to autouse fixture
    
    # --- Session 1: First call ---
    assert not is_rate_limited(tokens_used=TPM_LIMIT - 100)
    # Store state for Session 1
    s1_timestamps = session_request_timestamps.get().copy()
    s1_tokens = session_token_counts.get().copy()

    # --- Session 2 Setup & Call ---
    reset_context_vars() # Simulate context switch to Session 2
    assert not is_rate_limited(tokens_used=TPM_LIMIT - 50)
    # Session 2 state is not needed further for this test, but it has its own context now

    # --- Session 1 Again: Restore context and make another call ---
    # Simulate context switch back to Session 1
    session_request_timestamps.set(s1_timestamps)
    session_token_counts.set(s1_tokens)
    
    # This call for Session 1 should now be rate-limited (TPM_LIMIT - 100 + 101 > TPM_LIMIT)
    assert is_rate_limited(tokens_used=101)
    
    # Ensure Session 1's context was not modified by the rate-limited call
    assert session_request_timestamps.get() == s1_timestamps
    assert session_token_counts.get() == s1_tokens

    # Clean up for subsequent tests (though autouse fixture should handle this)
    reset_context_vars()

# Note: The original prompt mentioned using tokens for reset (e.g., session_request_timestamps.reset(token1)).
# However, contextvars.ContextVar.reset() takes a token returned by .set().
# For simulating different sessions, simply .set()-ing new/stored values is more straightforward
# unless we need to strictly revert to a *previous* state of the same context var within the same "session" flow.
# Here, we are simulating *different* sessions, so resetting to [] and then setting to stored state is fine.
# The autouse fixture handles the reset between tests.
# The test_concurrent_sessions_simulation now uses reset_context_vars() to simulate a fresh context for session 2,
# and then .set() to restore session 1's context.
# The tokens (token1, token2, etc.) are not strictly necessary if we manage state by .get() and .set()
# and reset with reset_context_vars() for simulating distinct contexts/sessions.

# A slight correction in test_exceed_rpm_limit logic:
# The RPM_LIMIT itself is inclusive. So, RPM_LIMIT requests should pass.
# The (RPM_LIMIT + 1)-th request should fail.
# The original test_exceed_rpm_limit was:
#   for _ in range(RPM_LIMIT): # This makes RPM_LIMIT calls, all should pass
#       assert not is_rate_limited(tokens_used=10)
#   assert is_rate_limited(tokens_used=10) # This is (RPM_LIMIT+1)th call, should fail
# This logic is correct. My comment above the test_exceed_rpm_limit was slightly off.
# The implementation of test_exceed_rpm_limit in the code block is correct.

# Let's refine test_exceed_rpm_limit for clarity
# It should be:
# Call RPM_LIMIT times, all pass.
# Call RPM_LIMIT + 1 time, this one fails.
# The loop for range(RPM_LIMIT) is correct for the first part.
# The current test_exceed_rpm_limit has a loop range(RPM_LIMIT -1), then one call, then another.
# Let's make it simpler:
# for _ in range(RPM_LIMIT):
#    assert not is_rate_limited(tokens_used=10)
# assert is_rate_limited(tokens_used=10) # This is the (RPM_LIMIT + 1)th call

# Re-checking test_exceed_rpm_limit:
# If RPM_LIMIT is 60:
# Loop range(59): 59 calls, all pass. Lists have 59 items.
# Next call (60th): passes. Lists have 60 items. len(timestamps) + 1 = 60 + 1 = 61.
# Oh, the condition is `len(request_timestamps) + 1 > RPM_LIMIT`.
# So, when len is 59, 59+1 = 60. If RPM_LIMIT is 60, 60 > 60 is false. Passes. Lists become 60.
# Next call, len is 60. 60+1 = 61. If RPM_LIMIT is 60, 61 > 60 is true. Fails.
# So, RPM_LIMIT calls should pass. The (RPM_LIMIT+1)th should fail.
# The current test_exceed_rpm_limit does:
# 1. Loop `RPM_LIMIT - 1` times (e.g., 59 times if RPM_LIMIT is 60). All pass. `len` is 59.
# 2. One more call. `len` was 59. `59 + 1 > 60` is false. Passes. `len` becomes 60.
# 3. One more call. `len` was 60. `60 + 1 > 60` is true. Fails.
# This is correct. My previous comment was analyzing it confusingly. The code is fine.

# For test_exceed_tpm_limit, after a call that is rate-limited, the context variables should NOT be updated.
# The current is_rate_limited function already behaves this way (it returns True before appending).
# Adding asserts to confirm this state.
# Done for test_exceed_tpm_limit.

# For test_concurrent_sessions_simulation:
# The use of .copy() is important when storing s1_timestamps and s1_tokens,
# because .get() returns a direct reference to the list in the context var.
# If we didn't copy, and if Session 2's operations somehow (even indirectly) mutated
# the list object that s1_timestamps pointed to (which they don't in this specific setup
# because reset_context_vars() creates new lists), it could lead to issues. Using .copy() is safer.
# This is already done in the code.

# The pytest fixture `auto_reset_context_vars` with `autouse=True` simplifies things
# by ensuring `reset_context_vars()` is called before each test function,
# providing a clean slate and good test isolation.
# This means we don't strictly need to call `reset_context_vars()` at the start of each test,
# but it doesn't hurt to be explicit if preferred. I'll rely on the fixture.

# Final check on `test_window_reset`:
# The logic seems fine. It modifies the timestamp of an existing entry to be very old,
# then checks if a new request is processed correctly (not rate-limited) and if the old entry is purged.
# The assertions `len == 1` and `tokens == [20]` confirm the purge and update.
# The timestamp check `(datetime.datetime.now() - new_timestamp).total_seconds() < 5` confirms it's a new timestamp.
# This looks good.
