library(dplyr)
library(tidyr)
source("R/dataset_writer.R")

epa_dataset_url <- "https://raw.githubusercontent.com/rfordatascience/tidytuesday/master/data/2019/2019-10-15/big_epa_cars.csv"
minimum_model_year <- 2015

model_family_patterns <- tribble(
  ~pattern, ~model_family,
  "^F150", "F-150",
  "^Ranger", "Ranger",
  "^Silverado", "Silverado",
  "^Colorado", "Colorado",
  "^Sierra", "Sierra",
  "^Canyon", "Canyon",
  "^1500", "Ram 1500",
  "^Tacoma", "Tacoma",
  "^Tundra", "Tundra",
  "^Frontier", "Frontier",
  "^Titan", "Titan",
  "^Ridgeline", "Ridgeline",
  "^Gladiator", "Gladiator"
)

resolve_model_family <- function(model_names) {
  families <- rep(NA_character_, length(model_names))
  for (row_index in seq_len(nrow(model_family_patterns))) {
    is_match <- is.na(families) & grepl(model_family_patterns$pattern[row_index], model_names)
    families[is_match] <- model_family_patterns$model_family[row_index]
  }
  coalesce(families, sub(" .*", "", model_names))
}

message("Downloading the EPA fuel economy dataset...")
epa_vehicles <- read.csv(epa_dataset_url, stringsAsFactors = FALSE)

pickup_inventory <- epa_vehicles %>%
  filter(year >= minimum_model_year, grepl("Pickup", VClass)) %>%
  select(make, model, year, VClass, cylinders, displ, trany, drive, fuelType, city08, highway08, comb08) %>%
  drop_na(cylinders, displ) %>%
  filter(trany != "") %>%
  group_by(make, model, cylinders, displ, drive) %>%
  slice_max(year, n = 1, with_ties = FALSE) %>%
  ungroup() %>%
  mutate(model_family = resolve_model_family(model)) %>%
  arrange(make, model_family, model, year, displ) %>%
  mutate(
    id = sprintf("INV-%04d", row_number()),
    name = paste(year, make, model),
    content = sprintf(
      "%s (%s %s family, %s). %.1fL %d-cylinder %s engine with %s and %s. Fuel economy: %d MPG city, %d MPG highway, %d MPG combined.",
      name, make, model_family, VClass, displ, as.integer(cylinders), tolower(fuelType),
      trany, drive, city08, highway08, comb08
    )
  ) %>%
  select(
    id, name, make, model, model_family, year,
    vehicle_class = VClass, cylinders, displacement_l = displ, transmission = trany,
    drive, fuel_type = fuelType, mpg_city = city08, mpg_highway = highway08,
    mpg_combined = comb08, content
  )

write_dataset(pickup_inventory, "epa_pickup_inventory.json")
message(sprintf("Processed %d pickup configurations from the EPA dataset.", nrow(pickup_inventory)))
