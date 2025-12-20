library(jsonlite)

safety_data <- list(
  list(
    topic = "Safety Features",
    details = "All Heavy Duty trucks come standard with reinforced steel frames and side-impact protection."
  ),
  list(
    topic = "Warranty",
    details = "Our 5-year/60,000-mile powertrain warranty covers all V6 and V8 engines. The EV battery has an extended 8-year protection plan."
  ),
  list(
    topic = "Family Safety",
    details = "For family applications, our lap-belt systems are rated #1 for child seat security in the Premium trim."
  )
)

write_json(safety_data, "../data/safety_warranty.json", pretty = TRUE, auto_unbox = TRUE)
print("Safety & Warranty Data generated!")
