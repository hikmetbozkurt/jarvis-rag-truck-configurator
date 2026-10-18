library(dplyr)
library(tidyr)
source("R/dataset_writer.R")

catalog <- read_dataset("vehicle_catalog.json")

as_table <- function(records, columns) {
  bind_rows(lapply(records, function(record) as_tibble(record[columns])))
}

models <- as_table(catalog$models, c("id", "name", "base_price_usd")) %>%
  rename(model_id = id, model_name = name)
engines <- as_table(catalog$engines, c("id", "name", "price_adder_usd")) %>%
  rename(engine_id = id, engine_name = name, engine_price_usd = price_adder_usd)
transmissions <- as_table(catalog$transmissions, c("name", "price_adder_usd")) %>%
  rename(transmission_name = name, transmission_price_usd = price_adder_usd)
trims <- as_table(catalog$trims, c("name", "price_adder_usd")) %>%
  rename(trim_name = name, trim_price_usd = price_adder_usd)

supported_engines <- bind_rows(lapply(catalog$models, function(model) {
  tibble(model_id = model$id, engine_id = unlist(model$supported_engine_ids))
}))

is_valid_transmission <- function(engine_name, transmission_name) {
  is_electric <- engine_name == "EV Dual Motor"
  is_direct_drive <- transmission_name == "Single-Speed Direct"
  is_v8_with_manual <- engine_name == "5.0L V8" & transmission_name == "6-Speed Manual"
  (is_electric == is_direct_drive) & !is_v8_with_manual
}

valid_configurations <- supported_engines %>%
  inner_join(models, by = "model_id") %>%
  inner_join(engines, by = "engine_id") %>%
  crossing(transmissions) %>%
  filter(is_valid_transmission(engine_name, transmission_name)) %>%
  crossing(trims) %>%
  mutate(total_price_usd = base_price_usd + engine_price_usd + transmission_price_usd + trim_price_usd)

format_usd <- function(amount) {
  paste0("$", format(amount, big.mark = ",", scientific = FALSE, trim = TRUE))
}

model_price_ranges <- valid_configurations %>%
  group_by(model_id, model_name, base_price_usd) %>%
  summarise(
    min_price_usd = min(total_price_usd),
    max_price_usd = max(total_price_usd),
    configuration_count = n(),
    .groups = "drop"
  ) %>%
  mutate(
    id = paste0("PRICE-", model_id),
    topic = "model_pricing",
    content = sprintf(
      "%s pricing: base MSRP %s. The %d valid configurations range from %s to %s depending on powertrain, transmission and trim.",
      model_name, format_usd(base_price_usd), configuration_count,
      format_usd(min_price_usd), format_usd(max_price_usd)
    )
  )

general_pricing_notes <- tibble(
  id = c("PRICE-BUDGET-TIERS", "PRICE-MAINTENANCE"),
  topic = c("budget_tiers", "maintenance"),
  content = c(
    "Budget tiers: Economy under $45,000 (light-duty I4 or V6 configurations with Base trim), Professional $45,000 to $55,000 (V6 or EV light-duty and entry heavy-duty builds), Executive above $55,000 (heavy-duty V8 or EV builds with Premium trim).",
    "Heavy Duty models (Ford F-350, RAM 2500) typically have about 15% higher annual maintenance costs than Light Duty models because of specialized suspension and high-torque components."
  )
)

market_pricing <- bind_rows(model_price_ranges, general_pricing_notes) %>%
  select(id, topic, model_name, base_price_usd, min_price_usd, max_price_usd, content)

write_dataset(market_pricing, "market_pricing.json")
