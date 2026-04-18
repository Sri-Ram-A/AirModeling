- Got all monitoring stations in bangalore : https://airquality.cpcb.gov.in/ccr/#/caaqm-dashboard-all/caaqm-landing
- Manually got each location : backend/data/stations.csv
```bash
git ls-files -s | awk '{print $4}' | xargs du -ch | tail -n 1
git lfs ls-files

# For commiting I did
sudo apt install git-lfs
# Then initialize it
git lfs install
# You should see something like:
Git LFS initialized.
# Verify installation
git lfs version
# If this fails → installation didn’t work.
Then proceed with tracking
git lfs track "*.csv"
# This will create/update:
.gitattributes
# Important: Fix your current state (you already staged files)
# You must re-add them properly:
git rm --cached backend/data/artifacts/*.csv
git add .
Then commit
git commit -m "Add large files via Git LFS"
# Then push
git push
```
