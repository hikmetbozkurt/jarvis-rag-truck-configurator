library(dplyr)
library(glue)
source("R/dataset_writer.R")

catalog <- read_dataset("vehicle_catalog.json")

engine_name_by_id <- setNames(
  vapply(catalog$engines, function(engine) engine$name, character(1)),
  vapply(catalog$engines, function(engine) engine$id, character(1))
)

describe_model <- function(model) {
  supported_engine_names <- paste(engine_name_by_id[unlist(model$supported_engine_ids)], collapse = ", ")
  list(
    id = glue("MANUAL-{model$id}"),
    title = glue("Technical Specification: {model$name}"),
    topic = "model",
    content = glue(
      "The {model$name} is a {model$category} pickup. {model$description} ",
      "Maximum towing capacity is {format(model$max_towing_lbs, big.mark = ',')} lbs and ",
      "maximum payload is {format(model$max_payload_lbs, big.mark = ',')} lbs. ",
      "Available powertrains: {supported_engine_names}."
    )
  )
}

describe_engine <- function(engine) {
  list(
    id = glue("MANUAL-{engine$id}"),
    title = glue("Powertrain Guide: {engine$name}"),
    topic = "engine",
    content = glue(
      "The {engine$name} is a {tolower(engine$fuel_type)} powertrain producing ",
      "{engine$horsepower} hp and {engine$torque_lb_ft} lb-ft of torque. {engine$description}"
    )
  )
}

find_recommendation_for_application <- function(application_name) {
  matching_rules <- Filter(function(rule) {
    identical(rule$type, "recommendation") &&
      identical(rule$conditions$application, application_name) &&
      is.null(rule$conditions$region)
  }, catalog$rules)

  if (length(matching_rules) == 0) {
    return("Our engineering team selects the drivetrain based on payload and duty cycle.")
  }
  matching_rules[[1]]$message
}

describe_application <- function(application) {
  list(
    id = glue("MANUAL-{application$id}"),
    title = glue("Application Guide: {application$name}"),
    topic = "application",
    content = glue(
      "{application$name}: {application$description} Chassis durability and torque ",
      "management are the key factors for this use case. ",
      "{find_recommendation_for_application(application$name)}"
    )
  )
}

technical_manual <- c(
  lapply(catalog$models, describe_model),
  lapply(catalog$engines, describe_engine),
  lapply(catalog$applications, describe_application)
)

write_dataset(technical_manual, "technical_manual.json")
