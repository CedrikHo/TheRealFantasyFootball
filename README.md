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

