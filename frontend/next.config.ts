import type { NextConfig } from "next";
import { PHASE_DEVELOPMENT_SERVER } from "next/constants";

export default function createNextConfig(phase: string): NextConfig {
  const isDevServer = phase === PHASE_DEVELOPMENT_SERVER;

  return {
    reactStrictMode: true,
    distDir: isDevServer ? ".next-dev" : ".next",
    webpack: (config, { dev }) => {
      if (dev) {
        config.cache = false;
      }

      return config;
    },
  };
}
