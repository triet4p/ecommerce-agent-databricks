# Task Summary: S4B-05

**Sprint:** Sprint 4b
**Task:** Eliminate the Stop/cancel terminal-state race

## Summary of Work

Added an active-stream registry with one shared cancellation promise and abort
controller. Stop and disconnect no longer race cancellation into failure.

## Files Modified

* `chat_ui/server/src/routes/turns.ts`
* `chat_ui/client/src/hooks/useChat.ts`
* `chat_ui/tests/server-routes.spec.ts`

## Testing

* **Status:** Passed
* **Evidence:** Cancel test observes one cancel call, zero fail calls, upstream
  abort, and final `cancelled` state.

## Additional Notes

The final logged-in browser Stop interaction remains in S4B-11.
