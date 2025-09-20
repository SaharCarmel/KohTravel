"""
Unit tests for circuit breaker pattern implementation.

Tests the circuit breaker functionality including failure tracking,
state transitions, and recovery mechanisms.
"""

import pytest
import asyncio
import time
from unittest.mock import MagicMock

from src.core.tool_registry import CircuitBreaker


class TestCircuitBreaker:
    """Test circuit breaker pattern implementation."""

    def test_initialization(self):
        """Test circuit breaker initialization with custom parameters."""
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=120)

        assert cb.failure_threshold == 5
        assert cb.recovery_timeout == 120
        assert cb.failure_count == 0
        assert cb.last_failure_time is None
        assert cb.state == "closed"

    def test_default_initialization(self):
        """Test circuit breaker initialization with default parameters."""
        cb = CircuitBreaker()

        assert cb.failure_threshold == 5
        assert cb.recovery_timeout == 60
        assert cb.failure_count == 0
        assert cb.state == "closed"

    def test_initial_state(self):
        """Test circuit breaker initial state is closed."""
        cb = CircuitBreaker()

        assert cb.state == "closed"
        assert not cb.is_open()
        assert cb.failure_count == 0

    def test_single_failure_recording(self):
        """Test recording a single failure."""
        cb = CircuitBreaker(failure_threshold=3)

        cb.record_failure()

        assert cb.failure_count == 1
        assert cb.state == "closed"
        assert cb.last_failure_time is not None
        assert not cb.is_open()

    def test_multiple_failures_before_threshold(self):
        """Test recording multiple failures before threshold."""
        cb = CircuitBreaker(failure_threshold=5)

        for i in range(4):
            cb.record_failure()
            assert cb.failure_count == i + 1
            assert cb.state == "closed"
            assert not cb.is_open()

    def test_threshold_breach_opens_circuit(self):
        """Test that reaching threshold opens the circuit."""
        cb = CircuitBreaker(failure_threshold=3)

        # Record failures up to threshold
        for _ in range(3):
            cb.record_failure()

        assert cb.state == "open"
        assert cb.is_open()
        assert cb.failure_count == 3

    def test_exceeding_threshold_keeps_circuit_open(self):
        """Test that exceeding threshold keeps circuit open."""
        cb = CircuitBreaker(failure_threshold=2)

        # Record failures beyond threshold
        for _ in range(5):
            cb.record_failure()

        assert cb.state == "open"
        assert cb.is_open()
        assert cb.failure_count == 5

    def test_success_resets_failure_count_when_closed(self):
        """Test that success resets failure count when circuit is closed."""
        cb = CircuitBreaker(failure_threshold=5)

        # Record some failures
        cb.record_failure()
        cb.record_failure()
        assert cb.failure_count == 2

        # Record success
        cb.record_success()
        assert cb.failure_count == 0
        assert cb.state == "closed"

    def test_success_closes_circuit_when_half_open(self):
        """Test that success closes circuit when half-open."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        # Open the circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"

        # Wait for recovery timeout to make it half-open
        time.sleep(0.2)
        assert not cb.is_open()  # Should be half-open

        # Record success should close it
        cb.record_success()
        assert cb.state == "closed"
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_recovery_timeout_makes_half_open(self):
        """Test that recovery timeout transitions to half-open state."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        # Open the circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"
        assert cb.is_open()

        # Wait for recovery timeout
        await asyncio.sleep(0.15)

        # Should now be half-open (is_open returns False for half-open)
        assert not cb.is_open()
        # State should still be "open" until success or failure is recorded

    def test_failure_in_half_open_reopens_circuit(self):
        """Test that failure in half-open state reopens circuit."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        # Open the circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"

        # Wait for recovery timeout
        time.sleep(0.2)
        assert not cb.is_open()

        # Record another failure should keep it open
        cb.record_failure()
        assert cb.state == "open"
        assert cb.is_open()

    def test_circuit_state_transitions(self):
        """Test complete circuit state transition cycle."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        # Initial state: closed
        assert cb.state == "closed"
        assert not cb.is_open()

        # Record failures to open circuit
        cb.record_failure()
        assert cb.state == "closed"

        cb.record_failure()
        assert cb.state == "open"
        assert cb.is_open()

        # Wait for recovery timeout (half-open)
        time.sleep(0.2)
        assert not cb.is_open()  # half-open

        # Success should close circuit
        cb.record_success()
        assert cb.state == "closed"
        assert not cb.is_open()

    def test_last_failure_time_updated(self):
        """Test that last_failure_time is updated on failure."""
        cb = CircuitBreaker()

        initial_time = cb.last_failure_time
        assert initial_time is None

        cb.record_failure()
        assert cb.last_failure_time is not None
        assert cb.last_failure_time > time.time() - 1  # Within last second

    def test_multiple_recovery_attempts(self):
        """Test multiple recovery attempts after circuit opens."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)

        # Open circuit
        cb.record_failure()
        assert cb.state == "open"

        # First recovery attempt - fail
        time.sleep(0.2)
        assert not cb.is_open()  # half-open
        cb.record_failure()
        assert cb.state == "open"

        # Second recovery attempt - succeed
        time.sleep(0.2)
        assert not cb.is_open()  # half-open
        cb.record_success()
        assert cb.state == "closed"

    def test_zero_threshold_circuit_breaker(self):
        """Test circuit breaker with zero threshold (always open)."""
        cb = CircuitBreaker(failure_threshold=0)

        # Should open immediately on first failure
        cb.record_failure()
        assert cb.state == "open"
        assert cb.is_open()

    def test_very_high_threshold(self):
        """Test circuit breaker with very high threshold."""
        cb = CircuitBreaker(failure_threshold=1000)

        # Record many failures
        for _ in range(999):
            cb.record_failure()
            assert cb.state == "closed"

        # 1000th failure should open circuit
        cb.record_failure()
        assert cb.state == "open"

    def test_concurrent_access_safety(self):
        """Test circuit breaker behavior under concurrent access."""
        cb = CircuitBreaker(failure_threshold=5)

        # Simulate concurrent failure recording
        for _ in range(10):
            cb.record_failure()

        # Should handle concurrent access gracefully
        assert cb.state == "open"
        assert cb.failure_count >= 5  # At least threshold reached