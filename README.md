# Train trips distances generation
This work has been done in the context of the organization of the IESF (Ingénieurs et Scientifiques de France) Scientific Convention named "From knowledge construction to its reception by the civil society", which will follow the model of the Citizen Conventions - more information available [here](https://conventions.iesf.fr/convention-connaissances/home) (in French).

The goal of these tools is to provide a semi-automatic pipeline for generating tables of all the train trips for all participants to a given event. In our case, that was the four weekends of the Scientific Convention. 

## 🔧 Installation

1. Install the dependencies:

```bash
pip install -r requirements.txt
```

## 📁 Folder structure:

The pipeline is based on the following files:

- `main.py` - Main script
- `PdfParserTickets.py` - Parses trips IDs from the tickets
- `Extract_SNCF_Trips_v5.py` - Extracts the exact trips via SNCF's API (French National Railway)
- `Duplicate_Manager_Excel.py` - Makes sure the trips are not double-counted
- `cities_to_GPS_cache_v2.py` - Geocoding of the cities of departures and destination
- `Verifications_Trajets_v1.py` - Checks the coherence of the trips for each traveler
- `signal_batch_distances_V3.py` - Finally, computes the distances for each segment of the trip of each traveler

## 📂 Input data organization

You must create a structure as follows :

```
./billets/
├── billets-train-XXX/
│   ├── ticket1.pdf
│   ├── ticket2.pdf
│   └── ...
├── billets-train-XXY/
│   ├── ticket3.pdf
│   └── ...
├── billets-train-XXZ/
```

**Important** : 
- The names of each sub-folder must respect the following  pattern `billets-train-XXX` where `XXX` will be used as the event's name
- The pipeline **automatically manages** each existing sub-folder
- You can have as many sub-folders as you need, one for each distinct event
- Names can vary `WE1`, `WE2`, `Weekend1`, `Jan2025`, etc. (the chain of characters after the second "-")

## 🚀 Usage

Call the whole pipeline:

```bash
python main.py
```