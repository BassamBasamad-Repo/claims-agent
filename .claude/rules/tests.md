---
description: Test file standards
globs: tests/*.py
---

# Test file standards

When working on any file in tests/:

## Test naming convention
- test_{module}_{scenario} format
- Examples: test_get_member_valid_id, test_hook_fires_above_threshold

## Required test categories per tool
- test_{tool}_happy_path
- test_{tool}_not_found  
- test_{tool}_invalid_input
- test_{tool}_error_category (verify errorCategory field)
- test_{tool}_is_retryable (verify isRetryable field)

## Never mock the data files in tests
- Use the actual mock JSON files in src/data/
- Reset state in setUp/teardown if tests write data
- Tests must be runnable in any order without side effects