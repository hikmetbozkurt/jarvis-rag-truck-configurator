library(dplyr)
source("R/dataset_writer.R")

efficiency_specs <- tibble(
  id = c("EFF-E1", "EFF-E2", "EFF-E3", "EFF-E4"),
  engine_name = c("2.0L I4 Turbo", "3.0L V6", "5.0L V8", "EV Dual Motor"),
  combined_mpg = c(24, 20, 15, NA),
  range_miles = c(NA, NA, NA, 320),
  rating = c("Excellent", "Good", "High Consumption", "Zero Emission"),
  eco_impact = c(
    "Low CO2 footprint for light city work.",
    "Balanced consumption for mixed daily use.",
    "Optimized for power over fuel economy.",
    "Best choice for environmental compliance in California."
  )
) %>%
  mutate(content = ifelse(
    is.na(range_miles),
    sprintf("%s efficiency: about %d MPG combined, rated %s. %s", engine_name, combined_mpg, rating, eco_impact),
    sprintf("%s efficiency: about %d miles of range per charge, rated %s. %s", engine_name, range_miles, rating, eco_impact)
  ))

write_dataset(efficiency_specs, "efficiency_specs.json")
