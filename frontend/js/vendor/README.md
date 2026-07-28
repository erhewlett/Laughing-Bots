# Vendored third-party code

Files here are not ours. They are committed rather than fetched so the app
works with no internet connection, which matters when the word cloud is being
demonstrated live.

| File | Library | Version | License | Source |
|---|---|---|---|---|
| `wordcloud2.js` | wordcloud2.js by Tim Guan-tin Chien | 1.2.3 | MIT | npm `wordcloud@1.2.3`, `src/wordcloud2.js`, copied unmodified |

To update, install the new version and copy the file straight across:

```bash
npm install wordcloud@<version>
cp node_modules/wordcloud/src/wordcloud2.js frontend/js/vendor/wordcloud2.js
```

Do not edit these files. Anything we need to change belongs in our own code.
