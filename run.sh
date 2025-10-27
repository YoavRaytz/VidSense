cd frontend
npm i react-router-dom
npm i react react-dom
rm -rf node_modules package-lock.json
npm install
npm run dev -- --port 5173 --host

ccd backend
PYTHONPATH="$PWD/.." WATCHFILES_FORCE_POLLING=true uvicorn app.main:app --reload --reload-dir app --port 8080

db docker by

