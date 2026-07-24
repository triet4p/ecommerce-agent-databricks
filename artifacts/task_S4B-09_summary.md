# Task Summary: S4B-09

**Sprint:** Sprint 4b
**Task:** Meet the Databricks graceful-shutdown contract

## Summary of Work

Retained the HTTP server, aborts active streams, closes idle/remaining
connections and the Lakebase pool, and enforces a 12-second deadline. The app
now runs Node directly so SIGTERM reaches this handler.

## Files Modified

* `chat_ui/server/src/index.ts`
* `chat_ui/server/src/routes/turns.ts`
* `chat_ui/app.yaml`

## Testing

* **Status:** Passed
* **Evidence:** Databricks log at `15:50:54Z` records both SIGTERM receipt and
  `Shutdown complete`; the following redeploy emitted no new system timeout.

## Additional Notes

Historical timeout entries remain in logs as evidence of the fixed npm-wrapper
failure.
