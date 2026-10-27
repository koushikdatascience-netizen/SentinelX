import {defineConfig} from "@playwright/test";

export default defineConfig({
 testDir:"./e2e",
 workers:1,
 retries:0,
 timeout:60000,
 use:{baseURL:"http://127.0.0.1:13001",trace:"retain-on-failure"},
 webServer:[
  {command:`"${process.env.E2E_PYTHON||"python"}" -m uvicorn tests.e2e_server:app --host 127.0.0.1 --port 18081`,
   cwd:"../backend",url:"http://127.0.0.1:18081/health",reuseExistingServer:false,
   env:{DATABASE_URL:"sqlite:///./sentinelx-e2e.sqlite3",JWT_SECRET:"offline-e2e-only-secret-at-least-32-characters",INFERENCE_PROVIDER:"demo",MODEL_API_KEY:"",ALLOW_PAID_INFERENCE:"false",ENABLE_LIVE_MULTIMODAL:"false",ENABLE_LEGACY_ENDPOINTS:"false",ALLOW_PUBLIC_REGISTRATION:"true",REGISTRATION_ALLOWED_EMAILS:"",AUTO_CREATE_SCHEMA:"true",CORS_ORIGINS:"http://127.0.0.1:13001"}},
  {command:"npm run start -- -p 13001",url:"http://127.0.0.1:13001",reuseExistingServer:false},
 ],
});
