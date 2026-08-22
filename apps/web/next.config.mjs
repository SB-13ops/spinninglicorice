/** @type {import('next').NextConfig} */
const nextConfig = {
  // Produce a self-contained build under .next/standalone containing only the
  // files needed to run the server. This keeps the production Docker image
  // small and lets us run `node server.js` without the full node_modules tree.
  output: "standalone",
};

export default nextConfig;
