# SignalDrop Frontend

React + TypeScript + Vite dashboard for the SignalDrop system.

The frontend consumes precomputed JSON artifacts via the FastAPI backend. It does no analytics of its own: all counts, shares, rankings, and topic groups come from the deterministic preprocessing pipeline. AI-generated labels and Key Findings are loaded as optional presentation layers.

## What it shows

- **Home screen** — generic SignalDrop intro with dataset cards. Click the active **Public Telegram Channels Dataset** card to open the Telegram analysis workspace; future loaders (Facebook, other public text sources) appear as disabled cards.
- **Telegram analysis workspace** — Key Findings, dataset overview, the Top declining trends list, expandable trend detail (monthly share chart, channel-level drops, example September posts), monthly post-volume chart, and methodology notes. A `← Back to datasets` button returns to the home screen.

Hash-routed: the home screen is the default; `#telegram` opens the dashboard.

## Local development

```bash
npm install
npm run dev          # starts Vite at http://localhost:5173
npm run lint
npm run build        # tsc + vite build → ./dist
```

In dev, Vite proxies `/api` and `/health` to `localhost:8000` (see `vite.config.ts`). For production builds, set:

```bash
VITE_API_BASE_URL=https://<app-runner-url>/api
```

Amplify reads this at build time.

## Project layout

```
src/
├── App.tsx                    # View routing (home / telegram), data loading
├── main.tsx                   # React root
├── api/client.ts              # fetch wrapper, calls FastAPI endpoints
├── components/
│   ├── HomeScreen.tsx         # Dataset selection
│   ├── Header.tsx             # Branding + theme toggle (variant: home | telegram)
│   ├── KeyFindings.tsx        # AI-generated or deterministic Key Findings
│   ├── OverviewCards.tsx      # Posts / Channels / Date range / Raw signals
│   ├── TrendList.tsx          # Top declining trends, click to inspect
│   ├── TrendDetail.tsx        # Per-trend chart, channels, example posts
│   ├── VolumeChart.tsx        # Monthly post-volume bars
│   └── MethodologyCard.tsx    # Methodology and thresholds
├── hooks/useTheme.ts          # Light/dark toggle, localStorage persistence
├── lib/labels.ts              # AI-label resolution + dedup
├── lib/insights.ts            # Deterministic Key Findings fallback
└── types/index.ts             # API response types
```

## Tech

- React 19 + TypeScript (strict)
- Vite 8
- Tailwind v4 (`@custom-variant dark` for `html.dark`)
- Recharts (line + bar charts)
- Lucide icons

## Conventions

- No analytics or scoring in the frontend. Anything that needs a number must come from a backend artifact.
- AI-label fallback chain: `short_label || label || trend.representative_topic || trend.topic`.
- The frontend filters out `is_displayable === false` consolidated groups from the main list. The full set is still served by the API for auditability.
