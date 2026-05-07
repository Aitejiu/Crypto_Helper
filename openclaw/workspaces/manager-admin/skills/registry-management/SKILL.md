---
name: registry-management
description: Manage the crypto_helper KOL registry lifecycle. Use when a request needs KOL lookup, listing, activation status interpretation, or mock add, disable, and archive operations.
---

# Registry Management

## Purpose

Define how crypto_helper agents interpret and modify KOL registry state without confusing registry entities with agent identities.

## When to use

Use this skill when:

- the user asks which KOLs are tracked
- a KOL name or alias must be resolved
- a dynamic KOL should be added
- a KOL should be disabled or archived
- the system must explain current lifecycle status

## Required tools

- `crypto_helper_registry_lookup`
- `crypto_helper_registry_list`
- `crypto_helper_registry_get_active`
- `crypto_helper_registry_add_mock`
- `crypto_helper_registry_disable_mock`
- `crypto_helper_registry_archive_mock`

## Procedure

1. Resolve KOL identity with `crypto_helper_registry_lookup`.
2. For list operations, prefer `crypto_helper_registry_get_active` unless the user asks for broader status coverage.
3. For add operations, create a dynamic KOL by default.
4. For disable operations, keep historical data and update lifecycle status.
5. For archive operations, preserve history while removing the KOL from normal active comparisons.
6. Report resulting status, limitations, and practical next steps.

## Safety rules

- KOLs are registry data entities, not default OpenClaw agents.
- All KOL resolution must go through `crypto_helper_registry_lookup`.
- Never invent a missing KOL.
- Added KOLs are dynamic by default.
- Disabled KOLs do not allow persona simulation.
- Archived KOLs keep historical data but are not active by default.
- Never hard-delete KOLs by default.
- Add, disable, and archive are mock admin operations.

## Required output format

- resolved or changed KOL status
- limitations
- next steps
