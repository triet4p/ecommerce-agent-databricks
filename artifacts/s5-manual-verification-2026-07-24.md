# Sprint 5 Manual Verification — 2026-07-24

## Authentication and live baseline

- CLI profile: `Ecommerce-Agent`
- Authenticated user: `trietlm0306@gmail.com`
- Catalog: `ecommerce_agent`
- Bundle commit: `201e1d04520ff991d469fc961d63bb34bb05ff9e`
- Initial React deployment:
  `01f18714e8061ccd96694f012ab53749`

## React browser parity

Conversation `0b74ece8-2b2c-40dc-89b5-26756e023c53`, renamed to
`S5 React parity temp`, proved:

- incremental preparing, tool, and text streaming phases;
- order tool arguments and result;
- terminal completion and Markdown heading/table/list/code rendering;
- two-turn replay and reload hydration;
- invalid-request UI and Retry without duplicate user messages;
- Stop without persisted user or partial assistant output;
- rename and delete flows;
- desktop and 390-by-844 mobile behavior without horizontal overflow.

Result: S5-17 passed.

The two temporary verification conversations were soft-deleted after evidence
collection; existing user conversation `Sprint 4b polished chat` was not
modified.

## Streamlit switch

Commands:

```text
databricks bundle deploy -t dev --profile Ecommerce-Agent --var chat_ui_source=ecommerce_agent
databricks bundle run ecommerce_agent_chat_ui -t dev --profile Ecommerce-Agent --var chat_ui_source=ecommerce_agent
```

Deployment `01f18718040d132f88e1417b53d2b66c` reached `SUCCEEDED`,
used source path `ecommerce_agent`, and started:

```text
streamlit run apps/streamlit_chat_ui/app.py
```

Authenticated browser execution failed:

```text
ModuleNotFoundError: No module named 'ecommerce_agent'
```

The source root is flattened to the contents of `ecommerce_agent/`; the nested
package name imported by `apps/streamlit_chat_ui/app.py` therefore does not
exist. The build also emitted:

```text
No dependencies file found. Skipping installation.
```

`ecommerce_agent/requirements.txt` is absent; dependencies exist only at
`ecommerce_agent/apps/streamlit_chat_ui/requirements.txt`.

Result: S5-09, S5-16, and S5-18 remain open.

## React restoration

Commands:

```text
databricks bundle deploy -t dev --profile Ecommerce-Agent
databricks bundle run ecommerce_agent_chat_ui -t dev --profile Ecommerce-Agent
```

Deployment `01f1871856bc198d8add093e495029b1` reached `SUCCEEDED`.
Logs proved `node server/dist/index.js`, production static serving, and
Lakebase schema v2. The pre-switch parity conversation reloaded with two user
messages, two assistant messages, one persisted tool card, and one Markdown
table.

Final live state: React restored and healthy. Sprint 5 closeout remains open
until the Streamlit blockers are fixed and the switch smoke is rerun.
