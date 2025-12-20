library(jsonlite)
library(dplyr)
library(tidyr)

# 1. Download External Real-World Data (EPA Vehicle Dataset)
# This is a high-quality dataset containing vehicles from 1984 to 2020
message("Downloading external EPA vehicle data...")
url <- "https://raw.githubusercontent.com/rfordatascience/tidytuesday/master/data/2019/2019-10-15/big_epa_cars.csv"
raw_data <- read.csv(url)

# 2. Process and Filter for Jarvis (Truck Specialist Persona)
# We only want Trucks and SUVs from recent years (e.g., 2015+)
master_truck_data <- raw_data %>%
  filter(year >= 2015) %>%
  filter(VClass %in% c("Standard Pickup Trucks 2WD", "Standard Pickup Trucks 4WD", 
                       "Standard Sport Utility Vehicle 4WD", "Special Purpose Vehicle 2WD")) %>%
  select(make, model, year, cylinders, displ, trany, drive, fuelType, city08, highway08) %>%
  # Create a clean "Jarvis Name" and "Description"
  mutate(
    full_name = paste(make, model, year),
    description = paste0("A ", year, " ", make, " ", model, " with a ", displ, "L ", cylinders, 
                         " cylinder engine. Features ", trany, " and ", drive, " drivetrain.")
  ) %>%
  # Clean up any missing values
  drop_na() %>%
  # Take a sample of 100 diverse vehicles to keep the RAG system focused
  group_by(make) %>%
  slice_head(n = 10) %>%
  ungroup()

# --- 3. Format for our Vector Database (FIXED VERSION) ---
# We use rowwise() so that a unique list is created for every single truck
inventory_json <- master_truck_data %>%
  rowwise() %>%
  mutate(
    metadata = list(list(
      make = make,
      model = model,
      year = year,
      engine_size = displ,
      transmission = trany,
      efficiency_city = city08,
      efficiency_hwy = highway08
    ))
  ) %>%
  ungroup() %>%
  mutate(id = paste0("INV-", row_number())) %>%
  select(id, name = full_name, metadata, description)

# --- 4. Export to the project data folder ---
write_json(inventory_json, "../data/master_inventory.json", pretty = TRUE, auto_unbox = TRUE)

print(paste("Successfully processed", nrow(master_truck_data), "external records into master_inventory.json"))
