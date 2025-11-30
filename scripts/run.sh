cd frontend
npm i react-router-dom
npm i react react-dom
rm -rf node_modules package-lock.json
npm install
npm run dev -- --port 5173 --host

cd backend
PYTHONPATH="$PWD/.." WATCHFILES_FORCE_POLLING=true uvicorn app.main:app --reload --reload-dir app --port 8080 --env-file ../.env

db docker by:
sudo docker run --name pgvector   -e POSTGRES_USER=tips   -e POSTGRES_PASSWORD=tips123   -e POSTGRES_DB=tipsdb   -p 5432:5432   -d ankane/pgvector:latest


