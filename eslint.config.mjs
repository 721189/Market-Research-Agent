import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import firebaseRulesPlugin from "@firebase/eslint-plugin-security-rules";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  firebaseRulesPlugin.configs["flat/recommended"],
  {
    files: ["**/*.ts", "**/*.tsx"],
    languageOptions: {
      parserOptions: {
        project: "./tsconfig.json",
      },
    },
  },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    "dist/**",
    "load_tests/**",
    "scripts/**",
    "eval/**",
    "tests/**",
    "backend/**",
    "infra/**",
  ]),
]);

export default eslintConfig;
