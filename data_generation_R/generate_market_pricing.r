library(jsonlite)
library(glue)

pricing_data <- list(
  list(
    category = "Budget Brackets",
    tiers = list(
      list(name = "Economy", range = "$35,000 - $45,000", description = "Base trims and I4 engines."),
      list(name = "Professional", range = "$45,000 - $65,000", description = "V6 engines and Sport trims."),
      list(name = "Executive", range = "$65,000+", description = "V8 or EV engines with Premium trims.")
    )
  ),
  list(
    category = "Maintenance Estimates",
    content = "Heavy Duty models (F-350, RAM 2500) typically have 15% higher annual maintenance costs than Light Duty models due to specialized suspension and high-torque components."
  )
)

write_json(pricing_data, "../data/market_pricing.json", pretty = TRUE, auto_unbox = TRUE)
print("Market Pricing Data generated!")
