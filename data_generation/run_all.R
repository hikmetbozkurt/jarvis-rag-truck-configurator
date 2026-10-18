generation_steps <- c(
  "R/generate_vehicle_catalog.R",
  "R/generate_technical_manual.R",
  "R/generate_market_pricing.R",
  "R/generate_efficiency_specs.R",
  "R/generate_safety_warranty.R",
  "R/process_epa_inventory.R"
)

for (step_path in generation_steps) {
  message(sprintf("Running %s", step_path))
  source(step_path, local = new.env())
}
