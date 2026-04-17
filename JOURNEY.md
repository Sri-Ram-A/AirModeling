- Got all monitoring stations in bangalore : https://airquality.cpcb.gov.in/ccr/#/caaqm-dashboard-all/caaqm-landing
- Manually got each location : backend/data/stations.csv
```bash
git ls-files -s | awk '{print $4}' | xargs du -ch | tail -n 1
```
