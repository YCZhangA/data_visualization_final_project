# Chicago Rent Policy Analysis

Analysis of housing rental policies and rent growth trends in the Chicago metropolitan area.

## Setup

```bash
conda env create -f environment.yml
conda activate chicago_rent
```

## Project Structure

```
data/
  raw-data/           # Raw data files
    acs_B25064_2024tract_median_rent.csv
    ACSDT5Y2024.B25070-Data.csv
    ACSDT5Y2024.B19013-Data.csv
    Zip_zori_uc_sfrcondomfr_sm_sa_month.csv
    tiger_tract/
     tl_2024_17_tract.shp.ea.iso.xml
     tl_2024_17_tract.shp.iso.xml
     tl_2024_17_tract.dbf
     tl_2024_17_tract.shp
     tl_2024_17_tract.shx
     tl_2024_17_tract.cpg
     tl_2024_17_tract.prj
  derived-data/       # Filtered data and output plots
    zillow_clean.csv
    acs_clean.csv
code/
  preprocessing.py
  make_static_plots.py
figures/
  static_zori_selected_zips.png
  static_choropleth_median_rent.png
streamlit-app/
  app.py
```

## Streamlit App

**Live Dashboard:** https://datavisualizationfinalproject-m7rnhvqfe9uemeai2vqwjt.streamlit.app/

> Note: Streamlit apps may need to be "woken up" if they have not been accessed in the last 24 hours.

## Data Sources

1. **American Community Survey (ACS)** – U.S. Census Bureau
   - Median gross rent and household income by census tract
   - Retrieved via the Census API

2. **Zillow Research Data** – Zillow Observed Rent Index (ZORI)
   - Monthly median rent time series by ZIP code
   - Downloaded from: https://www.zillow.com/research/data/

3. **U.S. Census Bureau TIGER/Line Shapefiles** — Census Tracts (TIGER Tracts)
	- Census tract boundary geometries for Illinois
   - Downloaded tl_2024_17_tract.zip from https://www2.census.gov/geo/tiger/TIGER2024/TRACT/, then unzipped into data/raw-data/

## Data Processing

- Raw data is stored in `data/raw-data/`
- All preprocessing is handled in `preprocessing.py`, which outputs cleaned files to `data/derived-data/`
- Large files (>100MB) are excluded from the repo via `.gitignore`

## How to Run

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Download raw data and place it in data/raw-data/:
   - TIGER/Line Census Tracts (Illinois, 2024)
Download tl_2024_17_tract.zip from:
https://www2.census.gov/geo/tiger/TIGER2024/TRACT/
Unzip it into: data/raw-data/tiger_tract/
   - Download Zip_zori_uc_sfrcondomfr_sm_sa_month.csv from:
https://www.zillow.com/research/data/
      - Select:
	      - Data Type: ZORI (Smoothed, Seasonally Adjusted): All Homes Plus Multifamily Time Series
	      - Geography: ZIP Codes

3. Run preprocessing:
   ```bash
   python preprocessing.py
   ```

4. Render the writeup:
   ```bash
   quarto render final_project.qmd
   ```

5. Run the Streamlit app locally:
   ```bash
   streamlit run streamlit-app/app.py
   ```
