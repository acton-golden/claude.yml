- uses: anthropics/claude-code-action@v1
  env:
    ANTHROPIC_BASE_URL: https://openrouter.ai/api
  with:
    anthropic_api_key: ${{ secrets.OPENROUTER_API_KEY }}
    prompt: |
      Review this PR for linting, test coverage, and security issues.
