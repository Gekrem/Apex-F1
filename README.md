# APEX F1

A bilingual Turkish/English Formula 1 fan publication prototype hosted on GitHub Pages.

## Automatic news collection and editorial approval

- GitHub Actions checks the configured RSS feeds every 6 hours (UTC), and can also be started manually from **Actions → Collect F1 news drafts → Run workflow**.
- Sources currently configured: Formula1.com, FIA News, and Autosport F1 RSS.
- New headlines and short RSS excerpts are added to `data/news.json` with `status: "draft"`.
- The workflow opens or updates a pull request titled **APEX F1: Review new news drafts**.
- Review every story against its original source. Add Turkish translations in `title_tr` and `summary_tr`, refine the English fields if needed, remove irrelevant/duplicate stories, and change only approved entries to `status: "published"`.
- Merge the pull request into `main`. GitHub Pages then publishes approved stories. Draft entries remain hidden from the public site.
- The public website displays only entries whose status is exactly `published` and links each headline to its original source.

## News item format

```json
{
  "id": "unique-id",
  "status": "published",
  "category": "F1 NEWS",
  "title_en": "English headline",
  "summary_en": "Short English summary from the RSS feed",
  "title_tr": "Türkçe başlık",
  "summary_tr": "Editör tarafından doğrulanmış Türkçe özet",
  "source_name": "Formula 1",
  "source_url": "https://...",
  "published_at": "2026-11-16T09:00:00Z",
  "collected_at": "2026-11-16T10:00:00Z"
}
```

## First-time setup in GitHub

1. Upload all files and folders in this package to the root of the existing `Apex-F1` repository, preserving folder paths. Allow overwriting `index.html` and `README.md`.
2. Commit the changes to the `main` branch.
3. Open **Settings → Actions → General** and ensure Actions are enabled. Under Workflow permissions, allow the workflow to create pull requests if that setting is shown.
4. Open **Actions → Collect F1 news drafts** and click **Run workflow** to test it. Scheduled checks then run every six hours.
5. Review the pull request created by the workflow. Do not merge unreviewed drafts as published content.

## Important notes

- This is a static site; it does not need a paid server or database.
- RSS provides headlines and excerpts, not permission to republish full articles. APEX F1 links to original publishers and uses short excerpts; write original summaries and respect each source's terms.
- Automatic collection is not automatic publication. Human review is required to prevent inaccurate, irrelevant, or duplicated stories.
- The collector does not use a paid AI translation service. Turkish translation and final editorial approval are intentionally left to the editor.
- RSS feeds and third-party GitHub Actions may change or become unavailable. Check workflow logs if a scheduled run fails.

## Editorial dashboard

- Open `editor.html` on the published GitHub Pages site to view the editorial dashboard.
- The dashboard reads `data/news.json`, shows draft/published counts, filters stories, and links to each original source.
- Use **New stories** to open the GitHub Actions workflow, **Review queue** to inspect pull requests, and **Edit JSON** to update translations/status in GitHub.
- GitHub Pages is static and cannot safely write to the repository by itself. The dashboard deliberately sends edits through GitHub's authenticated interface; never put a GitHub token or password in client-side code.

## AI-assisted bilingual editorial drafts

- The workflow at **Actions → APEX F1 AI editorial drafts** creates original Turkish and English headline/summary drafts from the English headline and short RSS excerpt already stored in `data/news.json`.
- It does not scrape or reproduce full publisher articles. It does not invent missing facts by design; thin excerpts are skipped or flagged for human verification.
- Every AI-assisted item remains `status: "draft"`. The workflow opens/updates a pull request; a human editor must verify the original source and approve publication.
- The workflow can run automatically after a human or editor-token commit changes `data/news.json` on `main`, or manually from the GitHub Actions page.
- Each run processes at most 15 eligible drafts to limit API usage.

### One-time OpenAI API setup

1. Create an API key in the OpenAI API platform. ChatGPT subscriptions and API billing are separate; API usage may incur charges.
2. In the GitHub repository, open **Settings → Secrets and variables → Actions → New repository secret**.
3. Set the secret name to exactly `OPENAI_API_KEY` and paste the API key as its value. Never put the key in website files, commits, issues, or chat messages.
4. Open **Actions → APEX F1 AI editorial drafts → Run workflow** to run a first test.
5. Review the pull request named **APEX F1: AI bilingual editorial drafts for review**. Do not publish without checking the original sources.

The workflow uses the OpenAI Responses API through the official Python SDK and structured JSON output. See the [OpenAI API quickstart](https://developers.openai.com/api/docs/quickstart) and [Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs).

