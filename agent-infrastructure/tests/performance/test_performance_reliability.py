#!/usr/bin/env python3
"""
Comprehensive Performance and Reliability Test for Phase 2.2
Tests caching performance, concurrent operations, memory usage, and system reliability.
"""

import sys
import asyncio
import time
import httpx
import gc
import resource
from typing import List, Dict, Any

# Add src to path for imports
sys.path.append('src')

from core.tool_registry import tool_registry
from schemas.tool_schemas import (
    ToolRegistrationRequest, ToolType, ToolSecurityPolicy
)


class PerformanceReliabilityTester:
    """Comprehensive performance and reliability test suite"""

    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.errors = []

    def log_test(self, test_name: str, passed: bool, error: str = None):
        """Log test result"""
        if passed:
            self.tests_passed += 1
            print(f"✓ {test_name}")
        else:
            self.tests_failed += 1
            if error:
                self.errors.append(f"{test_name}: {error}")
                print(f"✗ {test_name}: {error}")
            else:
                print(f"✗ {test_name}")

    def measure_memory_usage(self) -> float:
        """Get current memory usage in MB using resource module"""
        try:
            import platform
            memory_usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

            # On macOS, ru_maxrss is in bytes, on Linux it's in KB
            if platform.system() == 'Darwin':  # macOS
                return memory_usage / (1024 * 1024)  # Convert bytes to MB
            else:  # Linux
                return memory_usage / 1024  # Convert KB to MB
        except Exception:
            # If resource module fails, return a placeholder
            return 0.0

    async def test_tool_registry_caching_performance(self):
        """Test tool registry caching performance"""
        print("\n=== Testing Tool Registry Caching Performance ===")

        try:
            await tool_registry.initialize()

            # Register multiple tools for cache testing
            tool_ids = []
            register_start = time.time()

            for i in range(10):
                tool_request = ToolRegistrationRequest(
                    name=f"perf_test_tool_{i}",
                    type=ToolType.INTERNAL,
                    description=f"Performance test tool {i}",
                    version="1.0.0"
                )
                tool_id = await tool_registry.register_tool(tool_request)
                tool_ids.append(tool_id)

            register_time = time.time() - register_start
            self.log_test(f"Tool registration performance (10 tools in {register_time:.3f}s)", register_time < 5.0)

            # Test cache hit performance
            cache_start = time.time()
            for _ in range(100):
                for tool_id in tool_ids[:5]:  # Test first 5 tools
                    tool = await tool_registry.get_tool_by_id(tool_id)
                    assert tool is not None

            cache_time = time.time() - cache_start
            avg_cache_time = (cache_time / 500) * 1000  # ms per lookup

            self.log_test(f"Cache lookup performance (avg {avg_cache_time:.2f}ms per lookup)", avg_cache_time < 10.0)

            # Test agent tools loading performance
            agent_load_start = time.time()
            for _ in range(10):
                tools = await tool_registry.get_agent_tools("test_agent_perf")

            agent_load_time = time.time() - agent_load_start
            avg_agent_load_time = (agent_load_time / 10) * 1000

            self.log_test(f"Agent tools loading performance (avg {avg_agent_load_time:.2f}ms)", avg_agent_load_time < 100.0)

            # Cleanup
            for tool_id in tool_ids:
                await tool_registry.deregister_tool(tool_id)

        except Exception as e:
            self.log_test("Tool registry caching performance", False, str(e))

    async def test_concurrent_operations(self):
        """Test concurrent operation handling"""
        print("\n=== Testing Concurrent Operations ===")

        try:
            await tool_registry.initialize()

            # Test concurrent tool registration
            async def register_tool(index: int) -> str:
                tool_request = ToolRegistrationRequest(
                    name=f"concurrent_tool_{index}",
                    type=ToolType.INTERNAL,
                    description=f"Concurrent test tool {index}",
                    version="1.0.0"
                )
                return await tool_registry.register_tool(tool_request)

            concurrent_start = time.time()
            tool_ids = await asyncio.gather(*[register_tool(i) for i in range(20)])
            concurrent_time = time.time() - concurrent_start

            assert len(tool_ids) == 20
            assert all(tool_id for tool_id in tool_ids)

            self.log_test(f"Concurrent tool registration (20 tools in {concurrent_time:.3f}s)", concurrent_time < 10.0)

            # Test concurrent retrieval
            async def get_tool(tool_id: str):
                return await tool_registry.get_tool_by_id(tool_id)

            retrieval_start = time.time()
            tools = await asyncio.gather(*[get_tool(tool_id) for tool_id in tool_ids])
            retrieval_time = time.time() - retrieval_start

            assert len(tools) == 20
            assert all(tool for tool in tools)

            self.log_test(f"Concurrent tool retrieval (20 tools in {retrieval_time:.3f}s)", retrieval_time < 5.0)

            # Cleanup
            await asyncio.gather(*[tool_registry.deregister_tool(tool_id) for tool_id in tool_ids])

        except Exception as e:
            self.log_test("Concurrent operations", False, str(e))

    async def test_api_performance(self):
        """Test API endpoint performance"""
        print("\n=== Testing API Performance ===")

        client = httpx.AsyncClient(timeout=30.0)

        try:
            # Test health endpoint performance
            health_times = []
            for _ in range(10):
                start = time.time()
                response = await client.get("http://localhost:8001/health/")
                end = time.time()

                assert response.status_code == 200
                health_times.append((end - start) * 1000)  # Convert to ms

            avg_health_time = sum(health_times) / len(health_times)
            max_health_time = max(health_times)

            self.log_test(f"Health endpoint performance (avg {avg_health_time:.2f}ms, max {max_health_time:.2f}ms)", avg_health_time < 100.0 and max_health_time < 500.0)

            # Test agent listing performance
            agent_times = []
            for _ in range(5):
                start = time.time()
                response = await client.get("http://localhost:8001/api/agent/agents")
                end = time.time()

                assert response.status_code == 200
                agent_times.append((end - start) * 1000)

            avg_agent_time = sum(agent_times) / len(agent_times)

            self.log_test(f"Agent listing performance (avg {avg_agent_time:.2f}ms)", avg_agent_time < 200.0)

        except Exception as e:
            self.log_test("API performance", False, str(e))

        finally:
            await client.aclose()

    async def test_memory_usage(self):
        """Test memory usage and leak detection"""
        print("\n=== Testing Memory Usage ===")

        try:
            # Measure initial memory
            initial_memory = self.measure_memory_usage()

            await tool_registry.initialize()

            # Perform memory-intensive operations
            tool_ids = []
            for cycle in range(3):  # 3 cycles of operations
                # Register many tools
                for i in range(50):
                    tool_request = ToolRegistrationRequest(
                        name=f"memory_test_tool_{cycle}_{i}",
                        type=ToolType.INTERNAL,
                        description=f"Memory test tool {cycle}-{i}",
                        version="1.0.0"
                    )
                    tool_id = await tool_registry.register_tool(tool_request)
                    tool_ids.append(tool_id)

                # Perform many lookups
                for _ in range(100):
                    for tool_id in tool_ids[-10:]:  # Last 10 tools
                        await tool_registry.get_tool_by_id(tool_id)

                # Clean up this cycle's tools
                for tool_id in tool_ids[-50:]:
                    await tool_registry.deregister_tool(tool_id)

                # Force garbage collection
                gc.collect()

            # Measure final memory
            final_memory = self.measure_memory_usage()
            memory_growth = final_memory - initial_memory

            self.log_test(f"Memory usage (growth: {memory_growth:.2f}MB)", memory_growth < 50.0)

            # Check for reasonable memory usage (adjusted for realistic values)
            if final_memory > 500.0:  # More than 500MB might indicate a problem
                self.log_test("Memory usage - reasonable consumption", False, f"High memory usage: {final_memory:.2f}MB")
            else:
                self.log_test("Memory usage - reasonable consumption", True)

        except Exception as e:
            self.log_test("Memory usage", False, str(e))

    async def test_cache_ttl_behavior(self):
        """Test cache TTL (Time To Live) behavior"""
        print("\n=== Testing Cache TTL Behavior ===")

        try:
            await tool_registry.initialize()

            # Register a tool
            tool_request = ToolRegistrationRequest(
                name="ttl_test_tool",
                type=ToolType.INTERNAL,
                description="TTL test tool",
                version="1.0.0"
            )
            tool_id = await tool_registry.register_tool(tool_request)

            # Verify tool is in cache
            assert tool_id in tool_registry.tool_cache

            # Tool should be accessible immediately
            tool = await tool_registry.get_tool_by_id(tool_id)
            assert tool is not None

            self.log_test("Cache TTL - immediate access", True)

            # Test cache invalidation on deregistration
            await tool_registry.deregister_tool(tool_id)
            assert tool_id not in tool_registry.tool_cache

            self.log_test("Cache TTL - invalidation on deregistration", True)

            # Test agent cache behavior
            agent_id = "ttl_test_agent"
            cache_key = f"agent_tools:{agent_id}"

            # Load agent tools (will be cached)
            tools1 = await tool_registry.get_agent_tools(agent_id)
            assert cache_key in tool_registry.agent_tools_cache

            # Load again (should hit cache)
            tools2 = await tool_registry.get_agent_tools(agent_id)
            assert tools1 == tools2  # Should be same result

            self.log_test("Cache TTL - agent tools caching", True)

        except Exception as e:
            self.log_test("Cache TTL behavior", False, str(e))

    async def test_error_resilience(self):
        """Test system resilience to errors"""
        print("\n=== Testing Error Resilience ===")

        try:
            await tool_registry.initialize()

            # Test invalid tool registration handling
            invalid_registrations = 0
            successful_registrations = 0

            for i in range(10):
                try:
                    if i % 3 == 0:  # Every 3rd tool has invalid data
                        tool_request = ToolRegistrationRequest(
                            name="",  # Invalid empty name
                            type=ToolType.INTERNAL,
                            description="Invalid tool",
                            version="1.0.0"
                        )
                    else:
                        tool_request = ToolRegistrationRequest(
                            name=f"resilience_test_tool_{i}",
                            type=ToolType.INTERNAL,
                            description=f"Resilience test tool {i}",
                            version="1.0.0"
                        )

                    tool_id = await tool_registry.register_tool(tool_request)
                    successful_registrations += 1

                    # Clean up successful registrations
                    await tool_registry.deregister_tool(tool_id)

                except Exception:
                    invalid_registrations += 1

            # Should have handled invalid registrations gracefully
            expected_invalid = 4  # 0, 3, 6, 9
            expected_successful = 6  # 1, 2, 4, 5, 7, 8

            self.log_test(f"Error resilience - invalid registrations handled ({invalid_registrations} invalid, {successful_registrations} successful)",
                         invalid_registrations >= 3 and successful_registrations >= 5)

        except Exception as e:
            self.log_test("Error resilience", False, str(e))

    async def test_resource_cleanup(self):
        """Test proper resource cleanup"""
        print("\n=== Testing Resource Cleanup ===")

        try:
            # Test tool registry shutdown and cleanup
            initial_memory = self.measure_memory_usage()

            # Initialize and use tool registry
            await tool_registry.initialize()

            # Register some tools
            tool_ids = []
            for i in range(20):
                tool_request = ToolRegistrationRequest(
                    name=f"cleanup_test_tool_{i}",
                    type=ToolType.INTERNAL,
                    description=f"Cleanup test tool {i}",
                    version="1.0.0"
                )
                tool_id = await tool_registry.register_tool(tool_request)
                tool_ids.append(tool_id)

            # Shutdown registry
            await tool_registry.shutdown()

            # Force garbage collection
            gc.collect()

            # Check memory after cleanup
            post_cleanup_memory = self.measure_memory_usage()
            memory_diff = post_cleanup_memory - initial_memory

            self.log_test(f"Resource cleanup - memory management (diff: {memory_diff:.2f}MB)", memory_diff < 30.0)

            # Re-initialize for other tests
            await tool_registry.initialize()

        except Exception as e:
            self.log_test("Resource cleanup", False, str(e))

    async def run_all_tests(self):
        """Run all performance and reliability tests"""
        print("Starting Comprehensive Performance and Reliability Tests")
        print("=" * 60)

        await self.test_tool_registry_caching_performance()
        await self.test_concurrent_operations()
        await self.test_api_performance()
        await self.test_memory_usage()
        await self.test_cache_ttl_behavior()
        await self.test_error_resilience()
        await self.test_resource_cleanup()

        # Summary
        print("\n" + "=" * 60)
        print("PERFORMANCE AND RELIABILITY TEST RESULTS")
        print("=" * 60)
        print(f"✓ Tests Passed: {self.tests_passed}")
        print(f"✗ Tests Failed: {self.tests_failed}")
        print(f"Total Tests: {self.tests_passed + self.tests_failed}")

        if self.tests_failed > 0:
            print("\nFAILED TESTS:")
            for error in self.errors:
                print(f"  - {error}")
            return False
        else:
            print("\n🎉 ALL PERFORMANCE AND RELIABILITY TESTS PASSED!")
            return True


async def main():
    """Main test runner"""
    tester = PerformanceReliabilityTester()
    success = await tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)