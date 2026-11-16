# News data

`news.json` is the public site's approved-news data file. Entries with `status: "draft"` are hidden. The scheduled collector opens a pull request with new draft entries; verify them, add Turkish editorial text, and set approved entries to `status: "published"` before merging.
