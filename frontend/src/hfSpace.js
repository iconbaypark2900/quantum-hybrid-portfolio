/**
 * Hugging Face Space detection (CRA build-time env).
 * Set in `Dockerfile.hf` via `REACT_APP_HF_SPACE=1` before `npm run build`.
 */
export const isHfSpace =
  typeof process !== "undefined" &&
  process.env.REACT_APP_HF_SPACE === "1";
