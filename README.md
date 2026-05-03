# PlayerScope Analytics

A local football analytics demo that turns Transfermarkt player data into a recruiter-ready dashboard.

## What is included

- Search with player suggestions
- Profile table and player image
- Overview dashboard with overall score, output, availability, market momentum, stability, and discipline
- Scout Report tab with deterministic scouting verdicts, strengths, risks, next-analysis prompts, radar chart, and data-quality coverage
- Career Timeline tab combining strongest seasons, transfer moves, market-value peak, and major injury spells
- Market Lab tab with valuation trend labels, volatility, current-vs-peak ratio, and bear/base/bull value scenarios
- Stats tab with season and competition filters
- Market value, injury, and transfer tables with summary cards
- Player comparison lab for head-to-head player evaluation

## Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r dependencies.txt
python manage.py runserver
```

Backend URL:

```text
http://127.0.0.1:8000/app/
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend URL:

```text
http://127.0.0.1:5173
```

## Useful demo searches

- Marcus Rashford
- Bruno Fernandes
- Kylian Mbappe
- Bukayo Saka
- Lionel Messi

## Notes

The Stats tab may be slower on first load because Transfermarkt's detailed stats grid can require browser rendering. The backend caches rendered responses for repeat requests while the Django server stays running.
