# Fantasy Streamlit (baseline)

This is a minimal Streamlit app scaffold that accepts three CSV uploads, runs the project `compute` function (adapted from the Lambda code), and shows downloadable results with timestamps.

Files added:

- `app.py` — main Streamlit app (Home / Compute / Results tabs)
- `utils.py` — placeholder `compute(df1, df2, df3)` function
- `requirements.txt` — Python dependencies
- `Dockerfile` and `.dockerignore` — for containerized deployment

Run locally (virtualenv recommended):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Docker (build and run):

```bash
docker build -t fantasy-streamlit:latest .
docker run -p 8501:8501 fantasy-streamlit:latest
```

Deployment notes:

- Streamlit Community Cloud: push this repo to GitHub and follow Streamlit Cloud docs.
- AWS App Runner / App Runner on ECR: build and push the container image, then create an App Runner service.

**Desktop packaging (Nativefier)**
This repository includes convenience npm scripts that use `nativefier` to create desktop wrappers for the hosted Streamlit URL. The repo scripts call `npx` so you can build from the repository without a global install (recommended to add `nativefier` as a devDependency).

Quick summary of what we added to this repo:

- `package.json` contains per-platform scripts:
	- `npm run build-native-win-x64`
	- `npm run build-native-win-ia32`
	- `npm run build-native-linux-x64`
	- `npm run build-native-mac-x64`
	- `npm run build-native-mac-arm64`
	- `npm run build-native-all` — runs all of the above and places outputs in `native_build/`

How to use (recommended reproducible flow):

1. Ensure Node and npm are installed (or use `nvm` to manage versions):

```bash
node -v
npm -v
```

2. Install `nativefier` as a local devDependency (optional but recommended for reproducible builds):

```bash
npm install --save-dev nativefier
```

3. Build one platform (example — mac x64):

```bash
npm run build-native-mac-x64
```

4. Build all platforms into `native_build/` (this runs each per-platform script sequentially):

```bash
npm run build-native-all
```

Notes on `npx` vs global install:

- `npx nativefier ...` runs Nativefier on-demand (no global install). Our npm scripts use `npx` so the locally installed devDependency will be used when present, otherwise `npx` will fetch a matching version temporarily.
- If you prefer a system-wide CLI, install globally: `npm install -g nativefier` and run `nativefier <URL>` directly.

Where outputs go:

- By default the scripts create per-platform folders under `native_build/`, e.g. `native_build/MyFantasyApp-win32-x64`.

Caveats and cross-build notes:

- Cross-building is possible for many platforms but has limitations:
	- Building macOS `.app` artifacts generally requires a macOS build machine (some mac builds may fail on Linux/Windows). If you need mac `.app` artifacts reproducibly, run the mac builds on macOS runners or machines.
	- Building Windows installers may require `wine` to create certain installer formats when building on non-Windows hosts.
	- If you target Apple Silicon, use the `--arch arm64` script (we added `build-native-mac-arm64`). You can also build `universal` mac apps with `--arch universal` on macOS hosts.

Direct `npx` example (one-off):

```bash
npx nativefier --name "MyFantasyApp" "https://therealfantasyfootball-j5qcdzaa3apcognnt5gapl.streamlit.app/" --platform mac --arch x64
```

If you want, I can also:

- add a small GitHub Actions workflow that runs `npm ci` and `npm run build-native-all` on platform-appropriate runners and uploads artifacts to Releases, or
- tweak the scripts to create platform-specific installers (Squirrel, NSIS) which may require extra dependencies (`wine`, `makensis`) on CI.

If you'd like me to add an example GitHub Action that builds artifacts and uploads them, say which platforms/runners you prefer and I'll create it.

**Troubleshooting: Wine and Windows builds**

When building Windows artifacts on macOS, Nativefier (via electron-packager) may fail because it expects a `wine64` binary to exist. Typical failure looks like:

```
WrapperError: Wrapper command 'wine64' not found on the system.
```

What we did to resolve this locally:

1. Install a Wine variant (example using a community cask):

```bash
brew tap gcenx/wine
brew install --cask --no-quarantine gcenx/wine-devel
```

2. Create a `wine64` shim that points to the installed `wine` binary so tooling that expects `wine64` succeeds:

```bash
WINE_BIN="$(command -v wine)"
ln -s "$WINE_BIN" "$(brew --prefix)/bin/wine64"
# verify
command -v wine64
wine64 --version
```

What the commands do:

- `command -v wine` finds the installed `wine` executable and stores its path in `WINE_BIN`.
- `ln -s "$WINE_BIN" "$(brew --prefix)/bin/wine64"` creates a symbolic link named `wine64` in your Homebrew `bin` directory that points to the real `wine` binary (so `wine64` is on your `PATH`).
- `command -v wine64` and `wine64 --version` confirm the shim works.

Notes and caveats:

- A shim makes `wine64` detectable, but if the underlying `wine` build lacks full 64-bit support packaging may still fail. In that case either use a different Wine distribution or build Windows artifacts on a native Windows runner (GitHub Actions `windows-latest`) which avoids Wine entirely.
- On Apple Silicon you may need Rosetta or an x86 Homebrew install for some Wine builds; CI on `windows-latest` is the most robust option for Windows artifacts.
- If you prefer, I can add a GitHub Actions workflow that builds Windows artifacts on `windows-latest` and uploads them as build artifacts.

Recent changes to `utils.py`

- The `compute(df1, df2, df3)` function now merges the three uploaded CSVs on `id`, resolves duplicate-suffixed columns (e.g. `_df2`, `_df3`), and runs `CalculatePoints` to produce the final result DataFrame.
- `CalculatePoints` and helpers were adapted from your Lambda code; AWS calls were removed so the function returns a pandas DataFrame (no S3/DynamoDB I/O).
- Defensive behavior: the implementation uses a small helper so missing numeric columns do not raise errors (they default to zero Series). This makes the Streamlit UI more robust to slightly different CSVs.

Expected CSV filenames and UI notes

- The app shows three upload buttons labeled exactly as:
	- `ALLPLAYERSTATS.CSV`
	- `DEFENSIVESTATS.CSV`
	- `KICKERSTATS.CSV`
- The app will accept any uploaded file, but it displays a gentle warning if the uploaded filename doesn't match the expected name. The contents (columns) are what's important.

**Run locally**

Create a virtual environment, install dependencies, and start Streamlit:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

Open http://localhost:8501 in your browser. In the `Compute` tab upload the three CSVs (ALLPLAYERSTATS.CSV, DEFENSIVESTATS.CSV, KICKERSTATS.CSV), click `Submit`, then view/download the result on the `Results` tab.

Note: Streamlit binds to `0.0.0.0` when started with `--server.address 0.0.0.0`, but you must open the app in your browser using `http://localhost:8501` (or your machine's IP). Do not use `0.0.0.0` in the browser address bar.

**Team Handling**
- **Team CSV format:** Each team is uploaded as a CSV with columns at minimum: `first`, `last`, `id`, `position`. The `id` should match the `id` column in the computed FINALRESULTS.csv so players map correctly. If `id` is missing for a player, that player will be skipped in aggregation.
 - **Team CSV format (id required):** Each team is uploaded as a CSV. The `id` column (player id from FINALRESULTS.csv) is required and will be used for exact matching. Other columns (`first`, `last`, `player`, `position`) are optional and used only for presentation. Players that do not include an `id` in the team CSV will be skipped (the team will not be matched) — include `id` for every player for reliable aggregation.
	Note: every row (player) in a team CSV MUST include a non-empty `id` value. If any row lacks an `id`, the upload will be rejected and a warning shown in the UI when adding the team.
- **How aggregation works:** After you run `Compute` (upload the three required CSVs and click Submit) the app stores the computed FINALRESULTS.csv in session state. The `Results` tab uses `aggregate_team_scores()` to:
	- find rows in FINALRESULTS for each `id` listed in a team CSV,
	- compute `Total_Points = Total_Kicking_PTS + Total_defensive_PTS + Total_Offensive_PTS` for each matched player,
	- create a human-readable `calculation_str` (e.g. `5 + 3 + 10 = 18`) showing how the total was derived,
	- produce one per-team CSV containing the matched players and calculated fields, and one combined CSV for all teams.
- **Outputs & UI:** For each team you add in the `Teams` tab, the `Results` tab shows a collapsible summary with per-player rows, a bar chart of `Total_Points`, a team-level total, and a download button for that team's CSV. There's also a combined download for all teams.
- **Storage / persistence:** The app currently stores results and teams in `st.session_state` (in-memory). This means data is transient and lost on server restart or redeploy. For durable storage, save CSVs and metadata to an external store (S3, GCS, or a database); I can add S3 hooks if you'd like.


If you already have the sample CSVs in the repo root you can upload them directly from the file picker.

Testing with the example CSVs

- Place your three example CSVs in the repo root (or anywhere you like). If you named them according to the expected names above, the UI will show that name when you upload.
- From the app `Compute` tab: upload the three files, the `Submit` button enables once all three are uploaded. Click `Submit` to run `compute()` and then open the `Results` tab to download the generated CSV (it will include a timestamp in the UI).

Notes on environment/activation

- To reactivate the project's virtualenv in a new shell: `source .venv/bin/activate` (macOS / Linux).
- If you want an automated setup, add a `setup.sh` containing the three commands above.


Virtual environment (recommended)

Create and use a local virtual environment so project dependencies stay isolated:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Notes on using the project's virtual environment:

- The repository uses the directory name `.venv` by convention. Many editors (VS Code) auto-detect this and will use it if present.
- To reactivate the environment in a new shell, run `source .venv/bin/activate` (macOS / Linux) or `\.venv\Scripts\Activate.ps1` (PowerShell on Windows).
- Add `.venv` to your `.gitignore` so the environment is not committed.
- If you prefer `poetry` or `pipenv`, include `pyproject.toml` or `Pipfile` instead and update instructions accordingly.

How teammates know to use this env:

- Include the setup steps (above) in this `README.md` so anyone cloning the repo follows them.
- Optionally add a short `setup.sh` that creates and activates the env and installs deps; developers can run it once.


Upload limit (global/shared)

This app uses a per-project Streamlit config (config.toml) to raise the server.maxUploadSize limit. Streamlit enforces a per-file upload limit (value is in MB), but for this project treat the limit as a global/shared guideline: keep the combined size of the three CSVs (ALLPLAYERSTATS.CSV, DEFENSIVESTATS.CSV, KICKERSTATS.CSV) below the configured maximum to avoid memory/timeouts.
We recommend setting maxUploadSize to a safe value (for example 2048 for ~2 GB per file) in config.toml. Note that hosting providers (Streamlit Community Cloud, proxies, or load balancers) may enforce their own limits.
See Streamlit docs for details: https://docs.streamlit.io/knowledge-base/deploy/increase-file-uploader-limit-streamlit-cloud



Streamlit URL as of Dec 21 2025. : https://therealfantasyfootball-j5qcdzaa3apcognnt5gapl.streamlit.app/