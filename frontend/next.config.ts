import path from "path";
import type { NextConfig } from "next";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const nextConfig: NextConfig = {
  // Monorepo: avoid picking a parent directory lockfile as the tracing root
  outputFileTracingRoot: path.join(__dirname, ".."),
};

export default nextConfig;
