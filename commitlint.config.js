module.exports = {
  extends: ["@commitlint/config-conventional"],
  rules: {
    "header-max-length": [2, "always", 100],
    "type-enum": [
      2,
      "always",
      ["feat", "fix", "docs", "chore", "refactor", "test", "ci", "style", "perf", "build", "revert"],
    ],
  },
};
