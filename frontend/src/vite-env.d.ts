/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_CACHE_STALE_TIME?: string;
  readonly VITE_CACHE_GC_TIME?: string;
  readonly VITE_OPENAI_API_KEY?: string;
  // Add other VITE_ prefixed environment variables here as needed
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
