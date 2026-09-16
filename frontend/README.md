# frontend/ — analyst dashboard (Next.js)

Owner: Adarsh (frontend), with Kshitij on UI/UX and QA.

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev        # http://127.0.0.1:3000
```

The backend must be running on `http://127.0.0.1:8000`. To run the whole stack instead,
see **Quick start** in the [root README](../README.md).

## Pages

| Route | File | Purpose |
| --- | --- | --- |
| `/` | `app/page.tsx` | Landing and system status |
| `/login` | `app/login/page.tsx` | Sign in, stores the session |
| `/dashboard` | `app/dashboard/page.tsx` | Observed traffic, five-step forecast, attack-stage verdict, feature explanations |
| `/alerts` | `app/alerts/page.tsx` | Saved forecasts, sorted by risk and recency |
| `/alerts/[id]` | `app/alerts/[id]/page.tsx` | One alert: risk, stage, ranked contributors, recommended actions |
| `/upload` | `app/upload/page.tsx` | CSV replay upload and job status |
| `/live` | `app/live/page.tsx` | Pick an authorised live Zeek sensor as the dashboard source |
| `/admin` | `app/admin/page.tsx` | Admin surface |

## Supporting code

| Path | Purpose |
| --- | --- |
| `components/ForecastCharts.tsx` | Hand-rolled SVG risk timeline, stage distribution, feature bars |
| `components/SessionNav.tsx` | Navigation and sign-out, reacts to session expiry |
| `components/SystemStatus.tsx` | Backend health card |
| `lib/api.ts` | The only place that talks to the API, typed against `docs/api/api-contracts.md` |
| `tailwind.config.ts` | Theme, including the `risk-*` colour tokens |

## Checks

```bash
npm test          # tsc --noEmit
npm run build     # production build, must pass before you push
```

## Rules

- **Add dependencies from inside this folder.** Running `npm install` at the repository
  root creates a phantom project whose packages never reach the Docker image.
- **Go through `lib/api.ts`.** No component calls `fetch` against the backend directly.
- **Rely on API fields,** not on database ID order: use `risk_score`, `risk_level`,
  `created_at`, and `status`.
- **Every screen needs empty, loading, and error states.** A backend failure shows a
  banner, never a blank page.
- **Charts are plain SVG** in `ForecastCharts.tsx`. No charting library is installed, and
  none is needed for the current visuals.
