library(dplyr)
library(tidyr)
source("R/dataset_writer.R")

# The catalog describes a fictional dealership line-up. Prices, ratings and
# rules are synthetic; they exist to give the assistant a consistent ground truth.

models <- tibble(
  id = c("M1", "M2", "M3", "M4"),
  name = c("Ford F-150", "Ford F-350", "RAM 2500", "GMC Sierra 1500"),
  make = c("Ford", "Ford", "RAM", "GMC"),
  category = c("Light Duty", "Heavy Duty", "Heavy Duty", "Light Duty"),
  base_price_usd = c(38500, 49500, 47000, 41500),
  max_towing_lbs = c(11000, 20000, 19000, 11500),
  max_payload_lbs = c(2100, 4000, 3500, 2200),
  description = c(
    "Versatile full-size pickup for mixed work and daily use.",
    "Super Duty truck built for heavy towing and severe service.",
    "Heavy-duty pickup with a rugged frame for demanding job sites.",
    "Premium light-duty pickup focused on comfort and technology."
  )
)

engines <- tibble(
  id = c("E1", "E2", "E3", "E4"),
  name = c("2.0L I4 Turbo", "3.0L V6", "5.0L V8", "EV Dual Motor"),
  fuel_type = c("Gasoline", "Gasoline", "Gasoline", "Electric"),
  cylinders = c(4, 6, 8, 0),
  displacement_l = c(2.0, 3.0, 5.0, 0),
  horsepower = c(270, 375, 400, 452),
  torque_lb_ft = c(310, 470, 410, 775),
  price_adder_usd = c(0, 3500, 6500, 12000),
  description = c(
    "Fuel-efficient four-cylinder for light city work.",
    "Balanced V6 for daily work and moderate towing.",
    "High-torque V8 for maximum towing and heavy loads.",
    "Zero-emission electric drivetrain with instant torque."
  )
)

transmissions <- tibble(
  id = c("T1", "T2", "T3"),
  name = c("6-Speed Manual", "10-Speed Automatic", "Single-Speed Direct"),
  price_adder_usd = c(0, 1500, 0),
  description = c(
    "Traditional manual gearbox for driver control.",
    "Smooth automatic tuned for towing and highway efficiency.",
    "Direct drive unit used only with electric drivetrains."
  )
)

trims <- tibble(
  id = c("TR1", "TR2", "TR3"),
  name = c("Base", "Sport", "Premium"),
  price_adder_usd = c(0, 4500, 9000),
  description = c(
    "Standard work-ready equipment.",
    "Performance-tuned suspension and styling.",
    "Luxury interior, advanced driver assistance and technology package."
  )
)

applications <- tibble(
  id = c("A1", "A2", "A3", "A4", "A5"),
  name = c("Logging", "Long-haul delivery", "Urban delivery", "Emergency Medical", "Construction"),
  description = c(
    "Heavy timber transport in rugged terrain.",
    "Extended highway transport between cities.",
    "Short-range stop-and-go delivery inside cities.",
    "Critical response vehicles that must stay reliable under load.",
    "On-site material and tool transport."
  )
)

supported_engines <- tribble(
  ~model_id, ~engine_id,
  "M1", "E1", "M1", "E2", "M1", "E4",
  "M2", "E2", "M2", "E3",
  "M3", "E2", "M3", "E3",
  "M4", "E1", "M4", "E2", "M4", "E4"
)

exclusion_reasons <- tribble(
  ~model_id, ~engine_id, ~reason,
  "M1", "E3", "The 5.0L V8 is reserved for the Super Duty F-350 chassis.",
  "M4", "E3", "The 1500-series chassis is not rated for the 5.0L V8 package."
)

build_compatibility_rules <- function() {
  model_engine_pairs <- crossing(model_id = models$id, engine_id = engines$id)

  model_engine_pairs %>%
    anti_join(supported_engines, by = c("model_id", "engine_id")) %>%
    left_join(exclusion_reasons, by = c("model_id", "engine_id")) %>%
    left_join(select(models, model_id = id, model_name = name), by = "model_id") %>%
    left_join(select(engines, engine_id = id, engine_name = name), by = "engine_id") %>%
    arrange(model_id, engine_id) %>%
    mutate(
      default_reason = sprintf("The %s is not offered with the %s.", model_name, engine_name),
      message = coalesce(reason, default_reason),
      id = sprintf("RULE-COMPAT-%s-%s", model_id, engine_id)
    ) %>%
    rowwise() %>%
    mutate(rule = list(list(
      id = id,
      type = "constraint",
      conditions = list(model = model_name),
      forbidden = list(engine = engine_name),
      message = message
    ))) %>%
    pull(rule)
}

engineering_rules <- list(
  list(
    id = "RULE-V8-TRANSMISSION",
    type = "constraint",
    conditions = list(engine = "5.0L V8"),
    forbidden = list(transmission = "6-Speed Manual"),
    message = "The 5.0L V8 requires the 10-Speed Automatic because of its torque output."
  ),
  list(
    id = "RULE-EV-TRANSMISSION",
    type = "constraint",
    conditions = list(engine = "EV Dual Motor"),
    required = list(transmission = "Single-Speed Direct"),
    message = "The EV Dual Motor drivetrain only works with the Single-Speed Direct unit."
  ),
  list(
    id = "RULE-DIRECT-DRIVE-EV-ONLY",
    type = "constraint",
    conditions = list(transmission = "Single-Speed Direct"),
    required = list(engine = "EV Dual Motor"),
    message = "The Single-Speed Direct unit is only available with the EV Dual Motor."
  ),
  list(
    id = "RULE-LOGGING-RECOMMENDATION",
    type = "recommendation",
    conditions = list(application = "Logging"),
    recommendation = "Ford F-350 with 5.0L V8",
    message = "Logging needs extreme torque. The Ford F-350 with the 5.0L V8 is the recommended setup for rugged terrain."
  ),
  list(
    id = "RULE-CALIFORNIA-URBAN-DELIVERY",
    type = "recommendation",
    conditions = list(region = "California", application = "Urban delivery"),
    recommendation = "EV Dual Motor",
    message = "Urban delivery fleets in California should use the EV Dual Motor to meet local emission targets."
  ),
  list(
    id = "RULE-LONG-HAUL-TRANSMISSION",
    type = "recommendation",
    conditions = list(application = "Long-haul delivery"),
    recommendation = "10-Speed Automatic",
    message = "Long-haul delivery benefits from the 10-Speed Automatic for highway efficiency and driver fatigue."
  ),
  list(
    id = "RULE-SPORT-TRIM-WHEELS",
    type = "recommendation",
    conditions = list(trim = "Sport"),
    recommendation = "Performance Wheels and Upgraded Brakes",
    message = "The Sport trim pairs best with Performance Wheels and Upgraded Brakes."
  )
)

as_supported_engine_lists <- function() {
  supported_engines %>%
    group_by(model_id) %>%
    summarise(supported_engine_ids = list(I(engine_id)), .groups = "drop")
}

catalog <- list(
  models = models %>% left_join(as_supported_engine_lists(), by = c("id" = "model_id")),
  engines = engines,
  transmissions = transmissions,
  trims = trims,
  applications = applications,
  rules = c(engineering_rules, build_compatibility_rules())
)

write_dataset(catalog, "vehicle_catalog.json")
