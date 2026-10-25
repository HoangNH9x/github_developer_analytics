# Deploy Streamlit — GitHub Developer Analytics

## App entry point
- Repository: `HoangNH9x/github_developer_analytics`
- Branch: `streamlit-final-dashboard`
- Main file: `streamlit_app.py`
- Dependencies: `requirements.txt`
- Data files: `data/processed/` and `Ass_GD1/`

## Deploy to Streamlit Community Cloud
1. Open https://share.streamlit.io and sign in with the GitHub account that owns the repository.
2. Select **Create app**.
3. Choose the repository `HoangNH9x/github_developer_analytics`.
4. Select branch `streamlit-final-dashboard`.
5. Set the main file path to `streamlit_app.py`.
6. In Advanced settings, choose Python 3.12, then select **Deploy**.
7. Wait for the build to finish. Streamlit will provide a public `*.streamlit.app` URL; open it and check each page before giving it to the instructor.

Official guide: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy

## Important notes
- The app reads CSV files already stored in this repository; it does not call the GitHub API at runtime.
- No `.env` or GitHub token is needed for this dashboard. Do not paste an API token into Streamlit Secrets.
- The activity counts are currently observed CSV records, not complete totals for every repository. The repository summary includes collection status so pending/partial results are visible.
- Commits are present for only 26 of the 952 repositories in the current snapshot; many repositories still show Pending. Issues and Pull Requests also include partial collection. Do not describe zero rows in a pending repository as confirmed zero activity.
- Country data for activity authors is based on public profile location, which may be blank or self-reported. It must not be interpreted as verified nationality or as the country of repository ownership.
- This branch is prepared for review/deployment. The `main` branch has not been overwritten.
