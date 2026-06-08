# Air Dashboard Backend

FastAPI backend for station readings, transport matrix generation, and source inversion.

## Run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Swagger UI:
- `/docs`
- `/redoc`

## Notes

- The backend expects:
  - `data/raw/stations.csv`
  - `data/artifacts/final_master_dataset.csv`
- If a timestamp is not provided, the API uses the latest complete snapshot.

I require you to write put google docs file (using the latex format) on the below topic
**Air Pollution Attribution**
The Aim of this project is to find the contributions of how pollution travels from one station to another station and effects these stations. Today the focus is on these different pollutant concentrations , but as a future scope this can be actually extended to others like transportation, building construction etc , therby showing how pollution level can be attributed.
- Write only formulas in Latex
- Write every content as google docs format , and use the attached notebooks and my explanation
- Wherver figures are required , write the figure name with the description , I will attach the Image there , maintain 2 columns format in that .docx file
This is my *journey* and explanation so follow accordingly 
- The 14 stations data in the year 2025 has been extracted from India CPCB website(Central Pollution Control Board) and the following has be carried as we proceed:

# The First step - Exploratory Data Analysis with Data Imputation (0_imputation.ipynb)
1. After finding missing pollutants data percentage and a heatmap of missing pollutants for each stations , the following pollutants were dropped : Block 4 — Dropping columns: ['o_xylene', 'xylene', 'vertical_wind_speed', 'ethyl_benzene', 'mp_xylene']
2. For missing data , like wind_direction , circular_interpolate was used , to understand which a .html file was written for readers
3. Now in the Imputation block we have :
   1. Forward fill for Cumulative columns like Rainfall, 
   2. Circular interpolation for wind direction
   3. Linear interpolation for gaps ≤ 6 hours = 24 steps (because dataset is recorded at 15 minutes frequency for every station)
   4. 1-hour rolling median (isolated spikes still missing)
   5. Same time, previous day (gap 6–48 hrs)
   6. Same time, previous week (gap 2–7 days)
   7. Monthly x Hour median
   8. Column-wide median (last resort)
   9. Even after this the wind_direction had 1 Lakh Null values which I have taken care of later and I made multiple graphs like (Percentage of Originally Missing values Reconstructed,and which kind of imputation is being used).After this We did a graph plotting analysis where I have plotted the original and imputed values for each station's each column in order to check that the imputation has not drastically affected the columns distribution

# The Second Step - Calculating the contributions using traditional methods without deeplearning
1. Selecting a specific timestamp for the given pollutant where all stations have appropriate value
2. Also I have provided the formulas used in symbolic representations , you can use them with proper explanation
3. After calculating the transport matrix, I have plotted a figure showing the log scale of transport matrix and the direction of wind, as well as networkx graph representation
4. Now I start with the ethods such as :
   1. Least Squares Method
   2. Non Negative Least Squares
   3. Tikhonov Regularization
   4. Truncated SVD
   5. And A table showing the Comparisos of this error
5. Then There s a graph representing Obsserved and Reconstructed C in order to show a validation
6. Then We move on to the Bayesian Inference 
7. I want you to explain these methods and if required put image links from internet if required,in order to make people understand each method importance
8. Finally there is an observed vs reconstructed across various methods (4th Figure)

# The Third Step - Calculating the contributions using deeplearning models
- Use whatever I have currently done in the notebook,the work is still going on , without repeating the imputation steps again try to try all Deeplernng related works here , and graphs which can be attached.
- Right Now I am in beginning stages , but I plan to move into GNN Based Models, and hence kind of provide a comparative analysis of different methods used (suggest me some methods from baseline to evidence in the report)


- If any extra images are required , or flowcharts are required do put image descriptions or links in bracket (or flowchart code , which I will replace later)