# Task: Add Routing Config Parser

## Description

Add routing configuration parsing to the audit processor Lambda. The Lambda should read a `ROUTING_CONFIG` environment variable containing JSON routing rules and build a lookup dictionary for routing events by `svm_name` and `junction_path`.

## Background

The audit processor currently sends all events to a default EventBridge bus. This task adds the foundation for optional routing where specific SVM/junction_path combinations can be directed to different destinations. The config is parsed once on module load for cold start efficiency.

## Reference Documentation

**Required:**
- Design: `.agents/planning/2026-02-11-routing-config/design/detailed-design.md`

**Note:** Read the detailed design document before beginning implementation for full context on the routing feature.

## Technical Requirements

1. Add `ROUTING_CONFIG` environment variable reading
2. Parse JSON config on module load (outside lambda_handler)
3. Build `_routes` dictionary with `(svm_name, junction_path)` tuple keys
4. Handle invalid/missing JSON gracefully with logging
5. Expose a function to look up routes by key

## Dependencies

- Existing `lambda/audit_processor/index.py`
- Python `json` module (already imported)
- Python `os` module (already imported)

## Implementation Approach

1. Add `ROUTING_CONFIG = os.environ.get('ROUTING_CONFIG', '')` after existing env vars
2. Add module-level `_routes = {}` dictionary
3. Add config parsing block that populates `_routes` on module load
4. Add `get_route(svm_name, junction_path)` helper function
5. Add error handling for malformed JSON

## Acceptance Criteria

1. **Valid Config Parsing**
   - Given a valid JSON ROUTING_CONFIG with routes array
   - When the Lambda module loads
   - Then `_routes` dict contains entries keyed by (svm_name, junction_path) tuples

2. **Empty Config Handling**
   - Given ROUTING_CONFIG is empty or not set
   - When the Lambda module loads
   - Then `_routes` dict is empty and no errors occur

3. **Invalid JSON Handling**
   - Given ROUTING_CONFIG contains invalid JSON
   - When the Lambda module loads
   - Then error is logged and `_routes` dict is empty (graceful degradation)

4. **Route Lookup**
   - Given a populated `_routes` dict
   - When looking up a route by svm_name and junction_path
   - Then the correct route config is returned, or None if not found

5. **Unit Test Coverage**
   - Given the routing config parser implementation
   - When running the test suite
   - Then tests cover valid parsing, empty config, invalid JSON, and route lookup

## Metadata

- **Complexity**: Low
- **Labels**: Lambda, Configuration, Routing, Parser
- **Required Skills**: Python, JSON parsing, error handling, unit testing
