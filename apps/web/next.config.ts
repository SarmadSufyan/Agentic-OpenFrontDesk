import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The floating dev-tools badge sits on top of the sidebar account menu; errors still surface.
  devIndicators: false,
  // Do not generate AGENTS.md / CLAUDE.md helper files for AI coding tools.
  agentRules: false,
};

export default nextConfig;
