library(jsonlite)
library(dplyr)

# --- 1. Define Parts ---

# Models
models <- data.frame(
  id = c("M1", "M2", "M3", "M4"),
  name = c("Ford F-150", "Ford F-350", "RAM 2500", "GMC Sierra 1500"),
  category = c("Light Duty", "Heavy Duty", "Heavy Duty", "Light Duty"),
  description = c("Versatile full-size pickup.", "Super-duty truck for heavy towing.", "Rugged heavy-duty performance.", "Premium light-duty truck.")
)

# Applications
applications <- data.frame(
  id = c("A1", "A2", "A3", "A4"),
  name = c("Logging", "Long-haul delivery", "Emergency Medical", "Construction"),
  description = c("Heavy timber transport in rugged terrain.", "Extended highway transport.", "Critical response and life support.", "On-site material and tool transport.")
)

engines <- data.frame(
  id = c("E1", "E2", "E3", "E4"),
  name = c("2.0L I4 Turbo", "3.0L V6", "5.0L V8", "EV Dual Motor"),
  description = c("Fuel-efficient 4-cylinder.", "Powerful V6 for daily use.", "High-torque V8 for max power.", "Zero-emission electric drivetrain.")
)

transmissions <- data.frame(
  id = c("T1", "T2", "T3"),
  name = c("6-Speed Manual", "10-Speed Automatic", "Single-Speed Direct"),
  description = c("Traditional manual.", "Smooth automatic.", "Optimized for EV.")
)

trims <- data.frame(
  id = c("TR1", "TR2", "TR3"),
  name = c("Base", "Sport", "Premium"),
  description = c("Standard features.", "Performance-tuned.", "Luxury and tech.")
)

# --- 2. Define Compatibility Rules ---
rules <- list(
  # Engineering Constraint
  list(
    condition = "Engine == '5.0L V8'",
    forbidden = "6-Speed Manual",
    message = "Correction: The 5.0L V8 engine requires the 10-Speed Automatic transmission due to high torque output."
  ),
  # Complex Model Rule
  list(
    condition = "Model == 'Ford F-150' & Engine == '5.0L V8'",
    forbidden = "Combination",
    message = "Correction: The Ford F-150 is currently optimized for V6 or EV options. The Heavy-Duty 5.0L V8 is reserved for the F-350 chassis."
  ),
  # Regional Rule: California
  list(
    condition = "Region == 'California' & Application == 'Long-haul delivery'",
    suggestion = "EV Dual Motor",
    message = "Regional Rule: In California, city-based delivery applications must use Electric or Propane engines to meet environmental standards."
  ),
  # Industry Expert Suggestion: Logging
  list(
    condition = "Application == 'Logging'",
    suggestion = "Ford F-350 with 5.0L V8",
    message = "Jarvis Tip: Logging requires extreme torque. I highly recommend the Ford F-350 with the 5.0L V8 engine for this rugged terrain."
  ),
  list(
    condition = "Trim == 'Sport'",
    suggestion = "Add 'Performance Wheels'",
    message = "Suggestion: The Sport trim pairs best with Performance Wheels for improved handling."
  )
)

# --- 3. Export to JSON ---
export_data <- list(
  parts = list(
    models = models,
    applications = applications,
    engines = engines,
    transmissions = transmissions,
    trims = trims
  ),
  rules = rules
)

# Save the JSON file as ground truth
write_json(export_data, "../data/vehicle_knowledge_base.json", pretty = TRUE, auto_unbox = TRUE)

print("Knowledge base updated with Models, Applications, and Regional Rules!")
