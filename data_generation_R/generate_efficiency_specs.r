library(jsonlite)

efficiency_data <- list(
  list(
    engine = "2.0L I4 Turbo",
    avg_mpg = 24,
    rating = "Excellent",
    eco_impact = "Low CO2 footprint for light city work."
  ),
  list(
    engine = "EV Dual Motor",
    range_miles = 320,
    rating = "Zero Emission",
    eco_impact = "Best for environmental compliance in California."
  ),
  list(
    engine = "5.0L V8",
    avg_mpg = 15,
    rating = "High Consumption",
    eco_impact = "Optimized for power over fuel economy."
  )
)

write_json(efficiency_data, "../data/efficiency_specs.json", pretty = TRUE, auto_unbox = TRUE)
print("Efficiency Specs generated!")
