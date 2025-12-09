# BBK Local UI

Ultra-minimal Next.js app for Bot Better Know.

## Run

```bash
cd apps/bbk-local-ui
npm install
npm run dev
```

Open http://localhost:3000 (or your LAN IP) and ensure BBK API is running at http://localhost:8081.

- `Upload & Process Audio` calls POST http://localhost:8081/bbk/upload-and-process
- `Start Training` calls POST http://localhost:8081/bbk/start-training

Logo path: `public/bbk-logo.png` (drop your logo file there).
