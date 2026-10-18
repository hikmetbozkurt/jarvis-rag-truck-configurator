library(dplyr)
source("R/dataset_writer.R")

safety_and_warranty <- tibble(
  id = c("POLICY-SAFETY", "POLICY-POWERTRAIN-WARRANTY", "POLICY-EV-BATTERY-WARRANTY", "POLICY-FAMILY-SAFETY"),
  topic = c("Safety Features", "Powertrain Warranty", "EV Battery Warranty", "Family Safety"),
  content = c(
    "All Heavy Duty trucks come standard with reinforced steel frames and side-impact protection.",
    "The 5-year/60,000-mile powertrain warranty covers all V6 and V8 engines.",
    "The EV Dual Motor battery is covered by an extended 8-year/100,000-mile protection plan.",
    "For family use, the Premium trim adds advanced driver assistance and the highest-rated child seat anchoring."
  )
)

write_dataset(safety_and_warranty, "safety_warranty.json")
