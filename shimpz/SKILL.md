---
name: shimpz-store
description: >-
  Operate the Shimpz Store app by calling its API — never reimplement its logic. Triggers on shimpz-store,
  Shimpz Store. AUTHOR: sharpen this so the agent knows exactly when to reach for this app.
---

# Shimpz Store

This app runs as the `shimpz-store-backend` service. **Orchestrate it by calling its HTTP API** (reuse over
reimplementation) — the running app already guarantees the functionality and its business rules:

    from shimpzbus import call
    result = call("shimpz-store-backend", "/your/route", "POST", json_body={})

## Operations

<!-- AUTHOR: list each named operation the agent should use, with inputs/outputs. e.g.
### Create a campaign
`POST /campaigns` {name, budget} -> {id} — creates a paused campaign; call /campaigns/{id}/launch to go live. -->

## Business rules

<!-- AUTHOR: the rules the agent MUST respect when orchestrating this app (limits, approvals, ordering). -->
